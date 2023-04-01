import torch
import os
import time
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

class RoundTripErrorifier(object):
    """
    Makes tagged and human-readable grammar errors in data.
    """
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-uk-ru")
        self.model = AutoModelForSeq2SeqLM.from_pretrained("Helsinki-NLP/opus-mt-uk-ru")
        self.tokenizer2 = AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-ru-uk")
        self.model2 = AutoModelForSeq2SeqLM.from_pretrained("Helsinki-NLP/opus-mt-ru-uk")

    def setup(self):
        # setting device on GPU if available, else CPU
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print('Using device:', device)
        print()

        #Additional Info when using cuda
        if device.type == 'cuda':
            print(torch.cuda.get_device_name(0))
            print('Memory Usage:')
            print('Allocated:', round(torch.cuda.memory_allocated(0)/1024**3,1), 'GB')
            print('Cached:   ', round(torch.cuda.memory_reserved(0)/1024**3,1), 'GB')

    def main(self, input_file, out_folder):
        self.setup()
        # creating the output folder
        if not os.path.exists(out_folder):
            os.mkdir(out_folder)

        # reading the file
        with open(input_file, 'r') as f:
            text = f.read()
            lines = text.split('\n')

        s = time.time()
        final_list = []
        t0 = time.time()
        unprocessed_counter = 0

        # traversing through the list
        for i in range(len(lines)):
            sentence = lines[i]
            # round-translating the sentence
            translated = self.model.generate(**self.tokenizer(sentence, return_tensors="pt", padding=True))
            out = [self.tokenizer.decode(t, skip_special_tokens=True) for t in translated]
            translated = self.model2.generate(**self.tokenizer(out, return_tensors="pt", padding=True))
            corrupted = [self.tokenizer2.decode(t, skip_special_tokens=True) for t in translated]
            # adding the sentence to the list
            final_list.append(corrupted[0])
            # estimating the time left
            if i != 0 and not i % 1000:
                print(f"{i} sentences were processed\nProjected time till the end: {(time.time() - t0)/3600/i*(len(lines)-i):.2} hours")
                print(f"{unprocessed_counter} sentences were not processed.")

        text = '\n'.join(final_list)
        with open(out_folder + "/source.txt", 'w') as f:
            f.write(text)
        print(time.time() - s)

        text = '\n'.join(lines)
        with open(out_folder + "/target.txt", 'w') as f:
            f.write(text)