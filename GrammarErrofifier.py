import spacy_udpipe
import pymorphy2
import os
import time
import json
import random
import sys
import pandas as pd
from datetime import datetime
from collections import Counter
from sklearn.model_selection import train_test_split
from helpers.classes.SpaceHandler import SpaceHandler
from helpers.classes.Inflector import Inflector
from helpers.classes.GrammarInterpreter import GrammarInterpreter


class GrammarErrofifier(object):
    """
    Makes tagged and human-readable grammar errors in data.
    """
    def __init__(self):
      self.morph = pymorphy2.MorphAnalyzer(lang='uk')
      self.space_handler = SpaceHandler()
      self.inflector = Inflector(self.morph)
      self.grammar_interpreter = GrammarInterpreter(self.space_handler, self.inflector)
      self.spacy_model = SPACY_UDPIPE_MODEL = spacy_udpipe.load_from_path(
          lang="uk",
          path="helpers.models.ukrainian-iu-ud-2.5-191206.udpipe"
          )
      self.matchings = {"PROPN":"NOUN","NOUN":"NOUN", "VERB":"VERB", "PRON":"NPRO", "DET":"NPRO","ADJ":"ADJF", "NUM":"NUMR"} #match POS for inflector to be readable
      self.p_mispreposition = 0.8 # preposition error probability
      self.p_misconjugation = 0.5 # misconjugation probability
      self.t_prep = tuple(["від", "для", "по", "через", "при", "про","згідно", "над",
          "під", "до", "з", "ради", "із", "зі", "на", "при", "за", "в", 
          "на", "з-за", "із-за", "щодо", "крім", "між", "перед", "біля"]) # list of preposition to preposition errors

    "finds vidminok of a word given pos, word. uses inflector"
    def find_vidm(self, pos, word):
      descr = self.inflector.describe_word(pos, word)
      d = self.inflector.d_reverse[pos] # the dictionary of converting raw description to a tag
      seq = list()
      for i in d.keys():
        seq.append(len(set(i.split()) & descr)) 
      return d[list(d.keys())[seq.index(max(seq))]] #шукає найбільше співпадіння між describe_word та словником описів відмінків

    "splits text into (word, pos). uses spacy"
    def split_by_words(self, text):
      i = 0
      splitted_by_words = [('$START', 'PUNCT')] # we'll treat the starting token as punctuation to not trigger the mova-institute model
      for token in self.spacy_model(text):
        splitted_by_words.append([
          token.text, #оригінал
          token.pos_, # частина мови
          ])
        i += 1
      return splitted_by_words

    # helper functions
    # moving appends to the previous tokens
    def append_fix(self, tokens, labels, pos_seqs, conjugables, prepositions):
      labels_new = []
      for i in range(len(labels)):
        # if it is an append, then move it to the previous tag
        if labels[i].startswith('$APPEND'):
          labels_new[i-1] = labels[i]
        # and then append the existing tag
        labels_new.append(labels[i])
      return tokens, labels_new, pos_seqs, conjugables, prepositions

    # removing empty tokens
    def remove_empty_tokens(self, tokens, labels, pos_seqs, conjugables, prepositions):
      tokens_new = [tokens[i] for i in range(len(tokens)) if tokens[i] != ''] # if a token is empty, it would not be added
      labels_new = [labels[i] for i in range(len(labels)) if tokens[i] != ''] # repeat everything for all other elements
      pos_seqs_new = [pos_seqs[i] for i in range(len(pos_seqs)) if tokens[i] != '']
      conjugables_new = [conjugables[i] for i in range(len(conjugables)) if tokens[i] != '']
      prepositions_new = [prepositions[i] for i in range(len(prepositions)) if tokens[i] != '']
      return tokens_new, labels_new, pos_seqs_new, conjugables_new, prepositions_new

    # preparing the sentence for future errorifying
    def prepare_sentence(self, sentence):
      tokens_and_pos = self.split_by_words(sentence) #use mova_institute to get tokens and part of speech for every word
      tokens =  [i[0] for i in tokens_and_pos]
      pos_seq = [i[1] for i in tokens_and_pos]
      conjugables = [pos in set(self.matchings) for pos in pos_seq]
      prepositions = [token.lower() in self.t_prep for token in tokens]
      labels = ['$KEEP' for i in range(len(tokens))]
      return tokens, labels, pos_seq, conjugables, prepositions

    # making an error in conjuctions
    def make_conjugable_error(self, token, label, pos_seq, conjugable, preposition): # TAKES IN ONE WORD'S PROPERTIES
      pos = self.matchings[pos_seq] # convert to morph POS tags
      l = list(self.inflector.d_straight[pos].keys()) #список усіх відмінювань для частини мови даного слова
      vidm = l[random.randrange(1, len(l)-1)] #random case minus the default one and callings to fix the bug with plurals
      try: # if we can identify the original vidm
        new_label = "$TRANSFORM_" + pos + "_" + self.find_vidm(pos, token)
        new_token = self.inflector.inflect_word(token, vidm, pos)
        if token != new_token:
          return new_token, new_label, pos_seq, conjugable, preposition # return the errorified token + tag
        else: #if landed on the same one
          return token, label, pos_seq, conjugable, preposition # nothing changes
      except: # if can't identify vidm
        return token, label, pos_seq, conjugable, preposition # nothing changes

    # make an error in prepositions
    def make_preposition_error(self, token, label, pos_seq, conjugable, preposition): # TAKES IN ONE WORD'S PROPERTIES
      x = random.random()
      if x < 0.6: # make deletes a little more likely than replaces
        label = f'$APPEND_{token.lower()}'
        token = ''
      else: # if replace
        new = preps[random.randint(0, len(preps)-1)] #appennd random propostions
        if new in t_prep and new != token.lower(): #catches some weird bug
          label = f'$REPLACE_{token.lower()}'
          token = new
      return token, label, pos_seq, conjugable, preposition

    # combine all the errorifying functions and apply them to a sentence
    def errorify_sentence(self, sentence):
      # dissect the words by properties
      tokens, labels, pos_seq, conjugables, prepositions = self.prepare_sentence(sentence)
      # for each element (word/punct)
      for i in range(1, len(tokens)):
        # probability error
        p_error = random.random()
        # if it is a preposition and no tag has been applied to the previous token, make a preposition error
        if prepositions[i] and labels[i-1] == '$KEEP' and p_error <= self.p_mispreposition:
          tokens[i], labels[i], pos_seq[i], conjugables[i], prepositions[i] = self.make_preposition_error(tokens[i], labels[i], pos_seq[i], conjugables[i], prepositions[i])
        # if we can misconjunct the word and it does not have any appends, then make a conjugation error
        if conjugables[i] and labels[i] == '$KEEP' and p_error <= self.p_misconjugation:
          tokens[i], labels[i], pos_seq[i], conjugables[i], prepositions[i] = self.make_conjugable_error(tokens[i], labels[i], pos_seq[i], conjugables[i], prepositions[i])
      # append fix
      tokens, labels, pos_seq, conjugables, prepositions = self.append_fix(tokens, labels, pos_seq, conjugables, prepositions)
      # remove the empty tokens
      tokens, labels, pos_seq, conjugables, prepositions = self.remove_empty_tokens(tokens, labels, pos_seq, conjugables, prepositions)
      assert len(tokens) == len(labels)
      return tokens, labels

    def main(self, input_file, out_folder):
      # creating the output folder
      if not os.path.exists(out_folder):
        os.mkdir(out_folder)

      # reading the file
      with open(input_file, 'r') as f:
        text = f.read()
        lines = text.split('\n')
        lines = lines[:500000]

      final_list = []
      t0 = time.time()
      misinterpreted_counter = 0
      unprocessed_counter = 0

      # traversing through the list
      for i in range(len(lines)):
        sentence = lines[i]
        # making the error
        # try except loop to catch the sentences not processed by pymorphy
        try:
          errorified = self.errorify_sentence(sentence)
          # adding the sentence to the list
          final_list.append(errorified)
        except:
            unprocessed_counter += 1
        # estimating the time left
        if i != 0 and not i % 10000:
            print(f"{i} sentences were processed\nProjected time till the end: {(time.time() - t0)/3600/i*(len(lines)-i):.2} hours")

      # splitting the dataset into train and dev
      train, dev = train_test_split(final_list, test_size=0.2, random_state=47)

      # showing the results
      print("Out of 500, " + str(unprocessed_counter) + " sentences were not processed by Pymorphy and way too many could not be interpreted correctly.")

      # saving the train and the dev datasets
      with open(out_folder + "/train.json", 'w') as f:
          json.dump(train, f) 

      with open(out_folder + "/dev.json", 'w') as f:
          json.dump(dev, f)

      "LABEL COUNTER"
      all_labels = []
      for sent in final_list:
        for label in sent[1]:
          all_labels.append(label)

      # count each label type
      label_counts = dict(Counter(all_labels).items())
      label_counts = dict(sorted(label_counts.items(), key=lambda item: item[1], reverse=True))


      "METADATA WRITER"
      # saving the metadata
      message = "########## Preprocess info ##########\n"

      # writing the datetime
      ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      message += f"Generation datetime: {ts}\n"

      # writing the sample
      message += f"Sample used: {input_file}\n"

      # writing the sentences size
      message += f"Number of sentences : {len(final_list)}\n"

      # writing the tokens size
      message += f"Number of tokens/tags : {len(all_labels)}\n"

      # writing the label vocab size
      message += f"Number of unique labels : {len(label_counts)}\n"
      message += '\n'

      # writing the label count
      message += "Label counts:\n"
      for key in label_counts:
        message += f'{key} : {label_counts[key]}\n'

      # saving the message itself
      with open(out_folder + '/metadata.txt', 'w') as final_file:
        final_file.write(message)

      print("Done!")