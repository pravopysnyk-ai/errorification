import random
import os

class InversionErrorifier(object):
    """
    Makes inversion errors in data.
    """
    def __init__(self):
        pass

    def switch_words(self, sentence):
        words = sentence.split()
        n = len(words)
        random_word_index = random.randint(0, n-1)
        for i in range(max(0, random_word_index - 2), min(n-1, random_word_index + 3)):
            if i != random_word_index:
                words[i], words[random_word_index] = words[random_word_index], words[i]
                break
        return ' '.join(words)

    def main(self, input_file, out_folder):
        # creating the output folder
        if not os.path.exists(out_folder):
            os.mkdir(out_folder)

        # reading the file
        with open(input_file, 'r') as f:
            text = f.read()
            lines = text.split('\n')

        out_sentences = []
        for sentence in dataset:
            errorified = self.switch_words(sentence)
            out_sentences.append(errorified)

        text = '\n'.join(out_sentences)
        with open(out_folder + "/source.txt", 'w') as f:
            f.writelines(text)

        text = '\n'.join(dataset)
        with open(out_folder + "/target.txt", 'w') as f:
            f.write(text)

        print("Done!")