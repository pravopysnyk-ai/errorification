import re
import os
import json
import time
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from collections import Counter
from helpers.classes.SpaceHandler import SpaceHandler

class PunctErrorifier(object):
    """
    Makes tagged and human-readable punctuation errors in data.
    """
    def __init__(self, space_handler=SpaceHandler()):
        self.space_handler = space_handler
        self.transfer_matrix = pd.DataFrame()
        self.marks = []

    def generate_transfer_matrix(self):
        """ For simplicity, we create the transfer matrix between marks.
        It incorporates deletions and additions by treating the absense of a mark
        as _ -- also the punctuation mark, like the empty set.
        transfer_matrix[',',';'] is the probability of comma to be converted to semicolon
        """
        self.marks = [' ', ',', ';', ':', chr(8212), '-', '.', '?', '!', chr(8230)] # Encoded punctuation marks

        transfer_matrix = pd.DataFrame(data = np.zeros((len(self.marks), len(self.marks))),
                                       index = self.marks, 
                                       columns = self.marks)

        """Hyperparameters of the errorifier. We concentrate on the most common mistakes"""
        # Let us denote the relative odds of every error: p_1:p_2:p_3:...
        transfer_matrix.loc[:, ' '] = 0.8 # deleting all punctuation in general

        transfer_matrix.loc[' ', ','] = 10 # extra comma
        transfer_matrix.loc[' ', ';'] = 1 # extra semicolon
        transfer_matrix.loc[' ', ':'] = 1 # extra colon
        transfer_matrix.loc[' ', chr(8212)] = 2 # extra dash
        transfer_matrix.loc[' ', '-'] = 1 # extra hyphen

        transfer_matrix.loc[',', ','] = 30 # kept comma
        transfer_matrix.loc[',', ' '] = 80 # missed comma
        transfer_matrix.loc[',', ';'] = 1 # comma by semicolon

        transfer_matrix.loc[';', ' '] = 5 # missed semicolon
        transfer_matrix.loc[';', ','] = 20 # semicolon by comma
        transfer_matrix.loc[';', chr(8212)] = 1 # semicolon by dash

        transfer_matrix.loc[':', ' '] = 1 # missed colon
        transfer_matrix.loc[':', ','] = 3 # colon by comma
        transfer_matrix.loc[':', chr(8212)] = 30 # colon by dash

        transfer_matrix.loc[chr(8212), ' '] = 90 # missed dash
        transfer_matrix.loc[chr(8212), ','] = 30 # dash by comma
        transfer_matrix.loc[chr(8212), ';'] = 1 # dash by semicolon
        transfer_matrix.loc[chr(8212), ':'] = 5 # dash by colon

        transfer_matrix.loc['-', ' '] = 6 # missed hyphen
        transfer_matrix.loc['-', chr(8212)] = 1 # hyphen by dash (uniting dash)

        transfer_matrix.loc[chr(8230), chr(8230)] = 1 # unchanged ellipsis

        transfer_matrix.loc['.', '?'] =  1 # into question
        transfer_matrix.loc['.', '!'] =  1 # into assertion
        transfer_matrix.loc['?', '.'] =  1 # no question
        transfer_matrix.loc['?', '!'] =  1 # question into assertion
        transfer_matrix.loc['!', '.'] =  1 # no assertion
        transfer_matrix.loc['!', '?'] =  1 # assertion into question

        # How much of the dataset we want to have errors? A lot, I guess
        """
        How many errors do we even want in one sentence? About 1 per 5 words
        """
        probability_of_error = 5/10 # p of error on a spot

        for i in range(len(self.marks)-2):
            transfer_matrix.iloc[i,:] = probability_of_error*transfer_matrix.iloc[i,:]/np.sum(transfer_matrix.iloc[i,:])
            transfer_matrix.iloc[i,i] = 1 - probability_of_error

        # setting up custom probabilities for deleting the punctuation
        to_spaces = .8
        transfer_matrix.loc[:,' '] = to_spaces
        norm = np.sum(transfer_matrix.iloc[:,1:], axis=1)
        for m in self.marks[1:]:
            transfer_matrix.loc[:,m]=(1-to_spaces)*transfer_matrix.loc[:,m]/norm

        # Added by MB on Jun 25: increase prob of no change for spaces:spaces
        no_change_if_space_prob = 0.95
        transfer_matrix.loc[' ',' '] = no_change_if_space_prob
        norm = np.sum(transfer_matrix.iloc[0:1,1:], axis=1)
        multiplier = (1-no_change_if_space_prob)/float(norm)
        for m in self.marks[1:]:
            transfer_matrix.loc[' ',m] = transfer_matrix.loc[' ',m]*multiplier

        def update_cell(transfer_matrix, char_from, char_to, prob):
            # set new prob
            transfer_matrix.loc[char_from, char_to] = prob 
            # normalize row
            norm = np.sum(transfer_matrix.loc[char_from, transfer_matrix.columns != char_to])
            multiplier = (1-prob)/float(norm)
            transfer_matrix.loc[char_from, transfer_matrix.columns != char_to] = transfer_matrix.loc[char_from, transfer_matrix.columns != char_to]*multiplier

        update_cell(transfer_matrix, ' ', ' ', 0.95) #to reduce number of deletes
        update_cell(transfer_matrix, ',', ' ', 0.4) #to reduce number of append_,
        update_cell(transfer_matrix, '.', ' ', 0.1) # to reduce number of append_.
        update_cell(transfer_matrix, '.', '?', 0.00005) #to reduce number of replace_.
        update_cell(transfer_matrix, '.', '!', 0.00005) #to reduce number of replace_.
        update_cell(transfer_matrix, '—', ' ', 0.90) #to increase number of append_-
        update_cell(transfer_matrix, ':', ' ', 0.90) #to increase number of append_:
        update_cell(transfer_matrix, '—', ',', 0.05) #to increase number of replace_-
        update_cell(transfer_matrix, ':', ',', 0.05) #to increase number of replace_:
        # generate the actual error matrix
        self.transfer_matrix = transfer_matrix
        return
    
    def tokenize_sentence(self, sentence):
        """
        Creates a list of tokens, where each space between words is a separate token
        Example: ["START", "", "Я", "", "вісім", "", "років", "", "бомбив", "", "Донбас", "," "вбив", "", "багатьох", ":", "дітей" "," "дорослих" "," "і", "", "стариків", "."]
        """
        # preparing the data
        # getting rid of extra spaces
        sentence = self.space_handler.space_stripper(sentence)
        # replacing the ellipsis with one symbol
        sentence = re.sub("\.\.\.", chr(8230), sentence)
        # separating the quotation marks
        sentence = re.sub('"', ' " ', sentence)
        # clinging the punctuation back to those fuckers
        sentence = re.sub(r"\s([.,;:?!—-…])", r"\1", self.space_handler.space_stripper(sentence)) 
        # fixing the contractions (ЭТО КОСТЫЛЬ, НУЖНО ЗАМЕНИТЬ В БЛИЖАЙШЕЕ ВРЕМЯ)
        sentence = re.sub(r'\.,', chr(512), sentence)
        sentence = re.sub(r'\.:', chr(513), sentence)
        sentence = re.sub(r'\.;', chr(514), sentence)
        # matching the words
        words = re.findall(self.space_handler.uwr, sentence)

        # matching the punctuation
        punctuation = re.split(self.space_handler.uwr, sentence)

        # adding it as empty/non-empty tokens
        # fixing edge cases for our beloved quotation marks
        punctuation[0] = ' '
        if punctuation[-1] == '':
            punctuation[-1] = ' '

        punctuation = [list(p)[0] for p in punctuation]
        tokens = ['$START']
        for i in range(len(words)):
            # adding everything to the token list
            tokens.append(punctuation[i])
            tokens.append(words[i])
        tokens.append(punctuation[-1])
        return tokens

    # generating the error
    def generate_the_error(self, correct_mark):
        p = np.random.random()
        k = 0
        while p > self.transfer_matrix.iloc[self.marks.index(correct_mark),:k+1].sum(): # this is to choose the option with the given discrete distribution
            k += 1
        incorrect_mark = self.marks[k]
        return incorrect_mark

    def errorify_and_tag(self, sentence):
        # tokenizing the sentence
        tokens = self.tokenize_sentence(sentence)
        # creating a list of labels of the same length
        labels = ['' for i in range(len(tokens))]
        
        # traversing through the list and generating errors for spaces between words
        for i in range(len(tokens)):
            # if it is a space, then the only option is to (de)generate a erroneous mark
            # so, the model needs to delete it
            if tokens[i] == ' ':
                imark = self.generate_the_error(' ')
                if imark != ' ': # if changed
                    labels[i] = "$DELETE" # place the label
                    tokens[i] = imark # put the incorrect mark in tokens instead of a space
                else:
                    labels[i] = "$KEEP" # if nothing changed

            # if it is a punctuation mark, then there are a few options which we might pick
            elif tokens[i] in self.marks:
                cmark = tokens[i] # retrieve the punctuation symbol
                imark = self.generate_the_error(cmark) # generate an error

                if imark == ' ': # means that we have deleted cmark and need to put it back. thus we need to connect append to the previous word or the punctuation mark
                    labels[i-1] = f"$APPEND_{cmark}"
                else: # we have not deleted it, so there are two options
                    if cmark == imark: # nothing changed
                        labels[i] = "$KEEP"
                    else:  # changed into another non-empty symbol
                        labels[i] = f"$REPLACE_{cmark}"
                    
                # putting the incorrect mark in the token list
                tokens[i] = imark
            # else we just keep the element
            else:
                labels[i] = "$KEEP"

            # making sure we haven't screwed anything up
            if len(tokens) != len(labels):
                print("Token list and label list do not match in length before space removal!")
            assert(len(tokens) == len(labels))    
        return tokens, labels

    # removing the spaces (as in пробел) between words
    def remove_space_tokens(self, tokens, labels):    
        for i in range(len(tokens)):
            # removing the tags from spaces
            if tokens[i] == ' ':
                labels[i] = ' '
        # removing both of those from the according lists
        tokens[:] = (t for t in tokens if t != ' ')
        labels[:] = (l for l in labels if l != ' ')
        # making sure that we haven't screwed anything up
        if len(tokens) != len(labels):
            print("Token list and label list do not match in length after space removal!")
        assert(len(tokens) == len(labels))
        return tokens, labels

    # applying tags and converting back into the original sentence
    def anti_tagger(self, tokens, labels):
        # empty sentence to be filled
        sentence = ''
        # interpreting the tags
        if "APPEND_" in labels[0]: # if begins with append
            sentence += labels[0][-1]
        for i in range(1, len(tokens)):
            if labels[i] == '$KEEP': # if nothing changes
                sentence += tokens[i]
            elif labels[i] == '$DELETE': # if we delete the token
                sentence += '' # pass
            elif 'APPEND_' in labels[i]: # if we need to append one
                sentence += tokens[i] + labels[i][-1]
            elif 'REPLACE_' in labels[i]: # and if we need to replace
                sentence += labels[i][-1]
            else:
                print("Unidentified tag")
            sentence += ' '
        # fixing the special symbols
        sentence = re.sub(chr(8230), '...', sentence)
        # returning
        sentence = re.sub(' " ', '"', sentence)
        sentence = re.sub(chr(512), '.,', sentence)
        sentence = re.sub(chr(513), '.:', sentence)
        sentence = re.sub(chr(514), '.;', sentence)
        return self.space_handler.fried_nails(sentence)

    # amalgaming all those functions together
    def new_errorifier_tagger(self, sentence):
        # doing the actual work
        tokens, labels = self.errorify_and_tag(sentence)
        tokens, labels = self.remove_space_tokens(tokens, labels)
        return tokens, labels

    def generate_final_list(self, lines):
        np.random.seed(42) # for reproducibility
        final_list = []
        t0 = time.time()

        print("Original length: " + str(len(lines)) + " sentences")

        # traversing through the list
        for i in range(len(lines)):
            l = lines[i]
            # making sure that the sentence is clean and ready to be preprocessed
            correct_sentence = self.space_handler.fried_nails(l)
            # making the error
            incorrect_sentence = self.new_errorifier_tagger(correct_sentence)
            # adding the sentence to the list
            # making sure that the interpreted sentence is the original one
            if self.anti_tagger(incorrect_sentence[0], incorrect_sentence[1]) == correct_sentence:
                final_list.append(incorrect_sentence)
            # else:
            #   print(l)
            # estimating the time left
            i += 1
            if not i % 10000:
                print(f"{(time.time() - t0)/60:.1} mins elapsed so far. {i} sentences were processed\nProjected time till the end: {(time.time() - t0)/3600/i*(len(lines)-i):.2} hours")

        print("Errorified length: " + str(len(final_list)) + " sentences")
        return final_list

    def make_human_readable(self, final_list, out_folder):
        # making the human-readable version of the data
        with open(out_folder + "/human-readable.txt", 'w') as f:
            # traversing through the list
            for sentence in final_list:
                # concatenating the list into a single errorified sentence
                new_sentence = self.space_handler.fried_nails(' '.join([sentence[0][i] + ' ' for i in range(len(sentence[0]))])[len("$START"):])
                # showing the tag-token alignment in a human-readable format
                tagged_sentence = ' '.join(sentence[0][i] + sentence[1][i] + ' ' for i in range(len(sentence[0])))
                # Interpreting the sentence
                interpreted_sentence = self.anti_tagger(tagged_sentence[0], tagged_sentence[1])
                # writing the sentences to the file
                f.write(new_sentence + '\n' + tagged_sentence + '\n' + interpreted_sentence + '\n')
        print("Human-readable sentences have been generated!")

    def generate_metadata(self, final_list, output_folder):
        "LABEL COUNTER"
        all_labels = []
        for sent in final_list:
            for label in sent[1]:
                all_labels.append(label)
        # count each label type
        label_counts = dict(Counter(all_labels).items())
        label_counts = dict(sorted(label_counts.items(), key=lambda item: item[1], reverse=True))
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

    def main(self, input_file, output_folder):
        """
        Driver function for generating the errors.
        """
        # reading the input data
        with open(input_file, 'r') as f:
            text = f.read()
            lines = text.split('\n')

        # creating the output folder
        if not os.path.exists(output_folder):
            os.mkdir(output_folder)

        self.generate_transfer_matrix()
        
        # generate the errors
        final_list = self.generate_final_list(lines)

        # splitting the dataset into train and dev
        train, dev = train_test_split(final_list, test_size=0.2, random_state=47)

        # saving the train and the dev datasets
        with open(output_folder + "/train.json", 'w') as f:
            json.dump(train, f) 

        with open(output_folder + "/dev.json", 'w') as f:
            json.dump(dev, f) 

        self.make_human_readable(final_list, output_folder)
        self.generate_metadata(final_list, output_folder)
        print("Done!")