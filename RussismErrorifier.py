import os
import time
import collections
import random
from transformers import pipeline
from helpers.classes.SpaceHandler import SpaceHandler

class RussismErrofifier(object):
    """
    Makes tagged and human-readable russism errors in data.
    """
    def __init__(self):
      self.space_handler = SpaceHandler()
      self.translator = pipeline(task="translation", model='Helsinki-NLP/opus-mt-uk-ru', device=0)

    # AY: I have no idea what any of the following does.
    # I can't attest that it is able to produce any output or even compiles
    # If you have any idea of what's going on or how to improve it, feel free to open a pull request
    def antichanger(self, cor_word):
      start = time.time()
      res = set()
      res.add(cor_word.lower())

      one_replace_keys =["ё" , "мя" , "е" , "ё" , "ие" , "е", "ль" , "ы", "аи" , "ьо", "лья" , "ень" , "сч", "елье" , "нье", "e"]
      one_replace_values = ["е", "м'я", "є", "ьо", "іє", "і", "лль","и", "аї","йо", "л’я",  "інь", "щ", "ілля", "ння", "ьо"]

      
      def function_one_replace():
        for index, key in enumerate(one_replace_keys):
          temp = list()
          for st in res:
              x = st.replace(key,one_replace_values[index])
              temp.append(x)
          res.update(set(temp))

      def function_all_to_all():
        lt = "ауоиеіє"
        for c1 in lt:
          for c2 in lt:
            if c1 != c2:
              temp = list()
              for st in res:
                  for i in range(len(st)) :
                    if (st[i] == c1):
                        x = st[:i] + c2 + st[ i + 1:]
                        temp.append(x);
                    x = st.replace(c1, c2)
                    temp.append(x)
              res.update(set(temp))
              if len(res) > 10000:
                return 
      
      def function_all_ending():
          temp = list()
          dict_end = {"тись" : "ться", "овать" : "увати",  "ать" : "ати", "леть" : "літи",
                      "ити" : "ить", "ишь" : "іш","ый" : "ий", "ние" : "ння"}
          for st in res:
            for key in dict_end :
              pos = st.rfind(key)
              if pos != -1:
                  x = st[:pos] + dict_end[key]
                  temp.append(x)
          res.update(set(temp))
        
      def function_exeption():
        temp = list()
        for st in res:
            pos = st.find("бес")
            if pos != -1:
                x =  "без"+ st[pos+3:] 
                temp.append(x)

            pos = st.find("ис")
            if pos != -1 and pos + 2 < len(st):
                if (st[pos + 2] not in "ауеоиіїяює"):
                  x =  "із"+ st[pos+2:] 
                  temp.append(x)

            if(st[-1] == "я" and st[-2] in "ауеоиіїяює"):
              temp.append(st[:-1])
            if(st[-1] == "ц"):
              temp.append(st+"ь")
            

        res.update(set(temp))
      function_one_replace()
      
      function_all_ending()
      
      function_exeption()
      
      function_all_to_all()
      
      return set(res)

    "For getting prob of error"
    def random_replace(self, prob):
      gen = random.randint(0, 100) / 100
      return gen < prob

    "For batch translating ukr to rus"
    def translate_and_append(self, words_to_errorify):
      wordset = [word[0] for word in words_to_errorify]
      translated = self.translator(wordset, batch_size=64)
      translated = [sent['translation_text'].lower() for sent in translated]
      for i in range(len(words_to_errorify)):
        words_to_errorify[i].append(translated[i])
      return words_to_errorify

    def generate_vocab(self):
      # impport list of all ukr words
      words = list()
      with open('helpers/dicts/wordlist.txt') as f:
          for line in f:
            if line:
              words.append(line.replace("\n", ""))
      words = set(words)

      #import frequency vocab
      myfile = open("helpers/dicts//frequency-vocab.txt", 'r')
      frequence_dict = {}
      for line in myfile:
          k, v = line.strip().split()
          frequence_dict[k.strip()] = int(v.strip())

      vocab = set(frequence_dict.keys())
      return vocab

    'Main function. Takes in list of corr sentences, outputs list of incorr sentences'
    def errorify_rus_dataset(self, dataset, prob):
      all_sentences = [] #list of all tokenized sentences
      for sentence in dataset:
        all_sentences.append(sentence.split(' '))

      # list of all words to errorify - we later use batch translation on them
      words_to_errorify = []
      for sent_id in range(len(all_sentences)):    
        for word_id in range(len(all_sentences[sent_id])):
            if self.random_replace(prob):
              words_to_errorify.append([all_sentences[sent_id][word_id], sent_id, word_id]) #first item on the list is ukr_word, second is sent_id, third is word_id

      # batch translate all words and append translated as final one
      words_to_errorify = self.translate_and_append(words_to_errorify)

      # AY: I gave up here. I don't know what the main function is doing. Good luck.

      # for each word in words to errorify, errorify and replace it in the original dataset
      for word_lst in words_to_errorify:
        word_ukr = word_lst[0]
        work_rus = word_lst[3]
        sent_id = word_lst[1]
        word_id = word_lst[2]
        is_capital = (word_ukr.capitalize() == word_ukr)
        if word_ukr == work_rus or len(word_ukr) < 2:
          continue
        interim = (set(self.antichanger(work_rus) )& vocab ) - words - set([work_rus]) 
        new_dict = {i:frequence_dict[i] for i in (interim)}
        variants = [pair[0] for pair in sorted(new_dict.items(), key=lambda item: -item[1])]
        i = random.randint(0, (len(variants)-1) %4)
        # if variants[i] does not exist (i dont know why it wouldn't) we skip
        if len(variants)==0:
          continue
        suggested_surzhik = variants[i]
        if is_capital:
          suggested_surzhik = suggested_surzhik.capitalize()
        all_sentences[sent_id][word_id] = suggested_surzhik

      output_sentences = []
      for sentence in all_sentences:
        output_sentences.append(space_handler.fried_nails(" ".join(sentence)).replace("ʼ ", "ʼ"))
      return output_sentences

    def main(self, input_file, out_folder):
      # creating the output folder
      if not os.path.exists(out_folder):
        os.mkdir(out_folder)

      # reading the file
      with open(input_file, 'r') as f:
        text = f.read()
        lines = text.split('\n')

      s = time.time()
      out = self.errorify_rus_dataset(dataset,0.01)
      print(time.time() - s)
      output_sentences = [sent + '\n' for sent in out]
      with open(out_folder + "/russism-applied", 'w') as f:
        f.writelines(output_sentences)
      print("Done!")