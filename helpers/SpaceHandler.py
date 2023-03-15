import re

class SpaceHandler(object):
    """
    handles spaces before and after punctuation
    functions:
    - space_stripper - strips extra spaces from text, used in space_oddity
    - space_oddity - adds extra spaces before punctuation for tokenization
    - fried_nails - removes extra spaces before punctuation for anti-tokenization
    """
    def __init__(self):
        self.us = "[А-ЩЬЮЯЄҐІЇЭЫЪа-щьюяєґіїэыъ'0-9a-zA-Z()%‰\"№\+]" # ukrainian word symbol + brackets + quotation marks + percentage sign (ыыы костыль) + russian symbols (ik but it is what it is)
        self.upr = r'[.?!,;:—-]' # ukrainian punctuation
        self.uwr = re.compile(self.us + "+") # Matches a word. We want our model to predict hyphens, thus I remove - from here

    def space_stripper(self, sentence): # to get rid of extra spaces
        sentence = re.sub(r"\s{2,}", ' ', sentence) # double+ spaces
        sentence = re.sub(r"^\s+", '', sentence) # a space in the beginning (if double, then has already been removed)
        sentence = re.sub(r"\s+$", '', sentence) # a space in the end
        sentence = re.sub(r'([0-9])([.?!,;:—-])\s([0-9])', r"\1\2\3", sentence) # spaces in punctuation between numbers
        return sentence

    def space_oddity(self, sentence): # to add spaces in between of punctuation
        sentence = self.space_stripper(sentence) # get rid of extra spaces
        words = re.findall(self.uwr, sentence) # match words
        punctuation = re.split(self.uwr, sentence) # split the remains over words. The punctuation will be both at the beginning and in the end
        i = 0 # the index of considered punctuation
        sentence = "" # dummy for the newly created sentence
        while i < len(punctuation) - 1: # end before the last punctuation
            sentence += ' '.join(list(punctuation[i])) + ' ' +  words[i] + ' ' # the symbols between words now get to be joined by spaces. Likely with several spaces if there were spaces
            i += 1
        sentence += ' '.join(list(punctuation[-1])) # add the last punctuation to account for them not having the word following
        return self.space_stripper(sentence) # strip the remaining spaces just in case

    def fried_nails(self, sentence): # the reversed function: to remove the extra spaces. Not 1-to-1 (or onto?), like the previous function
        sentence = re.sub('\xad', '', sentence)
        words = re.findall(self.uwr, sentence) # retrieve the words as usual
        punctuation = re.split(self.uwr, sentence) # retrieve the rest
        i = 0
        sentence = ""
        while i < len(punctuation) -1:
            sentence += ''.join(re.split(r'\s+', punctuation[i])) + ' ' +  words[i] # now we remove the convenient spaces from punctuation, losing info
            i += 1
        sentence += ''.join(re.split(r'\s+', punctuation[-1]))
        sentence = re.sub(chr(8212), " " + chr(8212) + " ", sentence) # the dash must be separated at all times, no matter what
        sentence = re.sub(r'\s*-\s*', "-", sentence) # the hyphen is considered to cling always
        quote_split = re.split(r'\s*"\s*', sentence) # now, we deal with quotation marks
        sentence = ""
        for i in range(len(quote_split)//2):
            sentence += quote_split[2*i] + ' "' + quote_split[2*i+1] + '" ' # The odd numbered mark is the left one, the even numbered is the right one.
        if len(quote_split) % 2:
            sentence += quote_split[-1]
        # else: # if the number of marks is odd
            # print("Лапки порахуй, мудило") # A suggestion to the user: "Sorry, the program would work incorrectly if you do not fix the quotation marks yourself"
        sentence = re.sub(r"\s([.,;:?!])", r"\1", self.space_stripper(sentence)) # The rest of the punctuation gets clinged
        sentence = re.sub(r"\(\s+", '(', sentence) # fix the left brackets avoiding the "(" case (three punctuation marks in a row)
        sentence = re.sub(re.compile(f"({self.us})(\()"), r'\1 \2', sentence) # uncling the left bracket from a word
        sentence = re.sub("\s+\)", ')', sentence) # in the same way
        sentence = re.sub('–', ' –', sentence) # put space before the dash
        sentence = re.sub(re.compile(f"(\))({self.us})"), r'\1 \2', sentence) # uncling the right bracket from a word
        sentence = re.sub(r'\s*-\s*', "-", sentence) # the hyphen is considered to cling always
        sentence = re.sub(r"\s*’\s*", "’", sentence) # same for apostrophes
        sentence = re.sub(r'"\s\(', '"(', sentence) # removing the space from " (
        sentence = re.sub(r'\)\s"', ')"', sentence) # removing the space from ) "
        sentence = re.sub(r'([0-9])([.?!,;:—-])\s([0-9])', r"\1\2\3", sentence) # spaces in punctuation between numbers
        return sentence
