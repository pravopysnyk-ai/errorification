import os
import sys
import time
import spacy_udpipe
import pymorphy2
from helpers.classes.Inflector import Inflector
from helpers.classes.SurzhGenerator import SurzhGenerator

class SurzhErrorifier(object):
    """
    Makes surzhik errors in data.
    """
    def __init__(self):
        self.space_handler = SpaceHandler()
        self.morph = pymorphy2.MorphAnalyzer(lang='uk')
        self.inflector = Inflector(self.morph)
        self.spacy_model = spacy_udpipe.load_from_path(lang="uk", path="helpers/models/mova_institute.udpipe")
        self.surzhik_generator = SurzhiksGenerator(self.inflector, self.spacy_model)

    def main(self, input_file, out_folder):
        # creating the output folder
        if not os.path.exists(out_folder):
            os.mkdir(out_folder)

        # reading the file
        with open(input_file, 'r') as f:
            text = f.read()
            lines = text.split('\n')

        dataset = lines
        # extract ukr key phrases which to look for
        ukr_key_phrases = [word[1][:-1] for word in surzhik_generator.surzhiks2]
        # convert it to pairs of keywords
        ukr_key_words = []
        for key_phrase in ukr_key_phrases:
            words = key_phrase.split(" ")
            ukr_key_words.append(words)

        # extract ids of relevant sentences (those that contain all key words for given keyword pair)
        relevant_id = {}
        for key_phrase in ukr_key_phrases:
            relevant_id[key_phrase] = []
        for sent_id in range(len(dataset)):
            sentence = space_handler.space_oddity(dataset[sent_id])
            for key_phrase_id in range(len(ukr_key_phrases)):
                phrase_present = True
                for word in ukr_key_words[key_phrase_id]:
                    # if any word is not present, phrase_present = false
                    el = " " + word + " "
                    phrase_present = phrase_present and (el in sentence)
                if phrase_present:
                    relevant_id[ukr_key_phrases[key_phrase_id]].append(sent_id)

        # extract # of  sentences for each category 
        for key_phrase in ukr_key_phrases:
            print(key_phrase + ': ' + str(len(relevant_id[key_phrase])))
        
        # extract 20 sentences for each category
        idxs_to_surzhify = []
        for key_phrase in ukr_key_phrases:
        idxs_to_surzhify += relevant_id[key_phrase][:20]

        sentences_to_surzhify = [dataset[id] for id in idxs_to_surzhify]

        s = time.time()
        out_sentences =[]
        for sent in sentences_to_surzhify:
            try:
                out_sentence = surzhik_generator.antisurzhifier(sent)
                out_sentence = space_handler.fried_nails(out_sentence)
            except:
                out_sentence = sent
            out_sentences.append(out_sentence)
        print(time.time() - s)

        text = '\n'.join(out_sentences)
        with open(out_folder + "/source.txt", 'w') as f:
            f.writelines(text)

        text = '\n'.join(sentences_to_surzhify)
        with open(out_folder + "/target.txt", 'w') as f:
            f.write(text)

        print("Done!")