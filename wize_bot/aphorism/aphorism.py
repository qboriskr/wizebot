import gzip
import random

import pickle
from os import listdir
from os.path import isfile, join
from fuzzywuzzy import fuzz, process

DATA_PATH = '/Users/boris/work/planetpython_telegrambot/data'
MODEL_NAME = 'aphorisms.model'


class AphorismStorage:
    def __init__(self):
        self.corpus = set()
        self.key_words = []

    def get_stats(self):
        stats = 'Aphorisms: %d\n' % len(self.corpus)
        stats += 'Word count: %d' % len(self.key_words)
        return stats

    def get_random(self):
        return random.choice(self.corpus)

    def get_fuzzy(self, kw, limit=1):
        if isinstance(kw, list):
            kw = ' '.join(kw)
        return process.extract(kw, self.corpus, limit=limit, scorer=fuzz.token_set_ratio)

    def prepare(self, mypath, model_name):
        punctuation = '.,:"''\\-=+()*&&^%$#@!«»'
        current = []
        files = [f for f in listdir(mypath) if isfile(join(mypath, f))]
        for file in files:
            if not file.endswith('.txt'):
                continue
            file_path = join(mypath, file)
            for line in open(file_path):
                line = line.strip()
                if line:
                    current.append(line)
                    continue
                if len(current) > 5:
                    current = []
                    continue
                current_af = ' '.join(current)
                words = current_af.split(' ')
                if len(words) < 2:
                    continue

                for w in words:
                    while len(w) and w[-1] in punctuation:
                        w = w[:-1]
                    if not len(w):
                        continue
                    while len(w) and w[0] in punctuation:
                        w = w[1:]
                    if not len(w):
                        continue
                    if w not in self.key_words:
                        self.key_words.append(w)
                self.corpus.add(current_af)
                current = []
        print('loaded %d aforisms' % len(self.corpus))
        print('found %d key words' % len(self.key_words))
        for w in self.key_words:
            print(w)
        with gzip.open(join(mypath, model_name), 'wb') as pf:
            pickle.dump(self, pf)

    def load(self, mypath, model_name):
        with gzip.open(join(mypath, model_name), 'rb') as pf:
            tmp = pickle.load(pf)
            self.corpus = list(tmp.corpus)
            self.key_words = tmp.key_words


APHORISMS = AphorismStorage()
