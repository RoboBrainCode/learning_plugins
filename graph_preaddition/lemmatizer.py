from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet
from nltk import pos_tag

Lemmatizer = WordNetLemmatizer()
morphy_tags = {
    'NN': wordnet.NOUN, 'JJ': wordnet.ADJ, 'VB': wordnet.VERB, 'RB': wordnet.ADV
}

def lemmatize(word):
    if word == None or len(word) == 0: return word
    treebank_tag = pos_tag([word])[0][1]
    morphy_tag = morphy_tags.get(treebank_tag[:2], wordnet.NOUN)
    return Lemmatizer.lemmatize(word, morphy_tag)