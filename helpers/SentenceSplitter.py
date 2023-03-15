class SentenceSplitter:
    def __init__(self, SPACY_UDPIPE_MODEL) -> None:
        self.SPACY_UDPIPE_MODEL = SPACY_UDPIPE_MODEL

    def detect_pos(self, word):
        return self.SPACY_UDPIPE_MODEL(word)[0].pos_

    #find list of heads for given sentence
    def detect_head(a):
        res = []
        for i in range(len(a)):
            if i == (a[i].head.i):
                res.append(0)
            res.append(a[i].head.i)
        return res

    def head_token(self, a):
        if a.i == (a.head.i):
            return 0
        else:
            return a.head.i

    def split_by_words(self, text):
        splitted_by_words = []
        i = 0
        loaded = self.SPACY_UDPIPE_MODEL(text)
        for token in loaded:
            splitted_by_words.append ([
                token.text, #оригінал
                token.lemma_, # лема
                token.pos_, # частина мови
                token.dep_, # синтаксична роль
                str(token.morph),# морфологічний опис слова 
                self.head_token(token) #індекс голови
            ])
            i += 1
        return splitted_by_words