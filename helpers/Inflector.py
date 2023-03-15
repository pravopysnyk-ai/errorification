class Inflector(object):
  def __init__(self, morph):
    self.morph = morph
    self.matchings = {"NOUN":"NOUN", "VERB":"VERB", "PRON":"NPRO", "DET":"NPRO","ADJ":"ADJF", "NUM":"NUMR"} #POS names -- "pymorphy":"mova_institute"
    num_infls = {"N":{"nomn"}, "R":{"gent"},"D":{"datv"},"Z":{"accs"},"O":{"ablt"},"M":{"loct"}}
    p_infls = {"N":{"nomn"}, "R":{"gent"},"D":{"datv"},"Z":{"accs"},
               "O":{"ablt"},"M":{"loct"}}
    n_infls = {"N":{"nomn"}, "R":{"gent"},"D":{"datv"},"Z":{"accs"},
               "O":{"ablt"},"M":{"loct"},"K":{"voct"}}
    a_infls = {"N":{"nomn"}, "R":{"gent"},"D":{"datv"},"Z":{"accs"},"O":{"ablt"},"M":{"loct"}}
    v_infls = {"Inf" : {"infn"}, "Pr1": {"pres", "1per"}, "Pr2" : {"pres", "2per"},
               "Pr3" : {"pres", "3per"}, "Fu1" : {"futr", "1per"}, "Fu2" : {"futr", "2per"},
               "Fu3" : {"futr", "3per"}, "FuPl" : {"futr", "plur"}, "PsMs" : {"past", "masc"}, "PsFe" : {"past", "femn"},
               "PsNe" : {"past", "neut"}, "PsPl" : {"past", "plur"}, "Imp1" : {"impr", "1per"},
               "Imp2" : {"impr", "2per"}}

    # щоб упростити запис відмінку ($TRANSFORM_NOUN_O), я додав у інфлектор "словник відмінок":{опис відмінку для pymorphy}. Наприклад, "Imp1" : {"impr", "1per"}
    # кожна частина мови має свій набір відмінків. таким чином, d_straight -- це "словник словників".
    # тобто, якщо мені на вхід дали {"O", "NOUN"}, то щоб отримати pymorphy-readable формат, прога зробить наступний шлях
    # d_straight["NOUN"]["O"] == {"ablt"}

    self.d_straight = {"NOUN": n_infls,
                  "ADJF": a_infls,
                  "VERB": v_infls,
                  "NUMR": num_infls,
                  "NPRO": p_infls,
                  "ADJS": a_infls}


    n_reverse = {" ".join(v): k for k, v in n_infls.items()}
    a_reverse = {" ".join(v): k for k, v in a_infls.items()}
    v_reverse = {" ".join(v): k for k, v in v_infls.items()}
    p_reverse = {" ".join(v): k for k, v in p_infls.items()}
    num_reverse = {" ".join(v): k for k, v in num_infls.items()}

    self.d_reverse = {"NOUN":n_reverse, "VERB":v_reverse,"ADJF":a_reverse, "NUMR":num_reverse, "NPRO":p_reverse}
    self.pos = ["NOUN", "VERB","ADJF", "NUMR", "NPRO"]

  # фіксить правопис слова
  def helpers(self, word, tag):
    if tag == "$TRANSFORM_NOUN_R":
      #код нижче робить правки для
      #ч.р. іменників 2ої групи родового відміннка з неправильним закінченням -а:
      #будинка в будинку
      if word[-1] == "а":
        assumption = word[:-1] + "у"
        arr = tag.split("_")
        pos = arr[1] #pos
        descr = self.describe_word(pos, assumption)
        if 'masc' in descr and 'gent' in descr: #якщо помінявши закінчення слово існуватиме в родовому відмнінку, то ми зробили все правильно
          return assumption
        else:
          return word
      elif word[-1] == "я":
        assumption = word[:-1] + "ю"
        arr = tag.split("_")
        pos = arr[1] #pos
        descr =  self.describe_word(pos, assumption)
        if 'masc' in descr and 'gent' in descr:
          return assumption
        else:
          return word
      else:
        return word
    else:
      return word

  def describe_word(self, part_of_speech, word):
    parser_database = self.morph.parse(word)  # contains all possible word's homonyms
    expected = list(filter(lambda x: part_of_speech in x.tag, parser_database))[0] # first in the list has greatest possibility score
    attributes = set(expected.tag._grammemes_tuple) # набір грамем слова
    attributes.discard(part_of_speech) # окрім частини мови
    return (attributes)

  # keeps capitalization of the input word for the output word
  def save_capitalization(self, input:str, output:str):
    if input.istitle():
      return output.capitalize()
    else:
      return output

  def inflect_word(self, input_word, case, part_of_speech, gender=None, quantity=None):
    """
    Receives word and it's part of speech. Should inflect it to desired case.
    Parameters gender, quantity and perf, if given and can, impact on resulted inflection.
    """
    parser_database = self.morph.parse(input_word)  # contains all possible word's homonyms

    appropriate = list(filter(lambda x: x.tag.POS == part_of_speech,
                              parser_database))  # chooses only ones which satisfy part of speech
    expected = appropriate[0]  # first in the list has greatest possibility score

    #це дозволяє юзати як літерне позначення відмінку (N, O, K ітд), так і через set ({nomn} , {ablt} ітд)
    if isinstance(case, set):
      inflection_props = __import__('copy').deepcopy(case) # gets formal case
    else:
      inflection_props = __import__('copy').deepcopy(self.d_straight[part_of_speech][case])  # gets formal case

    # verb is completely different beast, its case specifies all params
    if part_of_speech != "VERB":
      #деякі форми упорото працюють
      if quantity == "plur":
        inflection_props.add(quantity)
      elif gender is not None:  # word must have gender in singular so that it is not just an abstraction
        inflection_props.add(gender)  # even for noun*

      if quantity is None and gender is None:  # I assume this may be unnecessary due to mechanics of inflect method
        if expected.tag.gender is not None:  # It probably doesn't change those params if they have not been specified as arguments
          inflection_props.add(expected.tag.gender)
        if expected.tag.number is not None:
          inflection_props.add(expected.tag.number)
    try:
      return self.save_capitalization(input_word, expected.inflect(inflection_props).word)
    except:
      return input_word
    
    
  def norm(self, pos, word):
    """
    returns normal form -- infinitive -- of a word
    """
    try:
      parser_database = self.morph.parse(word)
      return list(filter(lambda x: pos in x.tag, parser_database))[0].normal_form
    except:
      return word

  def get_infl(self, pos, word):
    """
    returns inflection
    """
    if pos == "VERB":
      parser_database = self.morph.parse(word)
      descr = list(filter(lambda x: pos in x.tag, parser_database))[0].tag
      if (descr.person, descr.tense) == (None, None):
        return {"infn"}
      if descr.tense == "past":
        return {descr.gender, descr.tense}
      return {descr.person, descr.tense}
    else:
      parser_database = self.morph.parse(word)
      #print(list(filter(lambda x: pos in x.tag, parser_database))[0].tag)
      return {list(filter(lambda x: pos in x.tag, parser_database))[0].tag.case}
  

  def get_number(self, pos, word):
    """
    returns inflection
    """
    parser_database = self.morph.parse(word)
    return list(filter(lambda x: pos in x.tag, parser_database))[0].tag.number

  def get_gender(self, pos, word):
    """
    returns inflection
    """
    parser_database = self.morph.parse(word)
    return list(filter(lambda x: pos in x.tag, parser_database))[0].tag.gender

  #returns what is a part of speech of w.
  #це тимчасова функція, тому що частину мови треба перевіряти за Mova Institute. Але поки що нехай буде так
  pos = ["NOUN", "VERB","ADJF", "NUMR", "NPRO"]

#генерує всі можливі частини мови, які дане слово може набувати

  def check_pos(self, w):
      all_variants = self.morph.parse(w)
      s = [all_variants[i].tag for i in range(len(all_variants))] # всі теги
      res = set()
      for i in self.pos:
        for j in s:
          if i in j:
            res.add(i) #серед усіх тегів усіх слів додає лише той, який є частиною мови
      return res

  def is_sublist(self, sub, list):
      res = True
      for i in sub:
          res = res and (i in list)
      return res

  #генерує тег для пари слів, який порівняє правильне та неправильне слово.
  def check(self, n_incorr, n_corr):
      try:
          p = list(self.check_pos(n_incorr) & self.check_pos(n_corr))[0] #частина мови, до якої можуть віднесені обидва слова (щоб уникнути омонімів)
          description = self.describe_word(p, n_corr)
          case = None
          for i in (self.d_reverse[p].keys()):
              if is_sublist(i.split(), description):
                  case = self.d_reverse[p][i]
          return "TRANSFORM_" + p + "_" + case
      except:
          pass
      return None

  #перетворити слово в нормальне назад суто за тегом
  #наприклад, ("прийшла", "TRANSFORM_VERB_PsMs") -> прийшов
  def reverse_trans(self, word, tag):
      descr = tag.split("_")
      pos = descr[1]
      return self.inflect_word(word, descr[2], pos)