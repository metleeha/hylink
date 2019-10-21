# -*- coding: utf-8 -*-

from re import split
from networkx import Graph
from networkx import pagerank
from itertools import combinations
from sentence import Sentence

from konlpy.tag import Okt

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import normalize
import numpy as np

class TextRank(object):

    def __init__(self, text):
        self.text = text.strip()
        self.build()

    def build(self):
        self._build_sentences()
        self._extract_nouns()
        self._build_graph()
        # 문장 랭크 처리
        self.pageranks = pagerank(self.graph, weight='weight')
        self.reordered = sorted(self.pageranks, key=self.pageranks.get, reverse=True)
        # 단어 랭크 처리
        self.word_rank_idx = self.get_word_ranks(self.words_graph)
        self.sorted_word_rank_idx = sorted(self.word_rank_idx, key=lambda k: self.word_rank_idx[k], reverse=True)

    def _build_sentences(self):
        dup = {}
        # 0.1같은 실수형식이랑 .txt같은 파일형식 안잘리게 정규식으로 split
        # 풀어쓰면 아래 주석과 같은 기능
        # candidates = split(r'(?<=[^0-9])(?<=[^a-z])[\.|\n]', self.text)
        candidates = []
        for enter_line in split('\n', self.text): 
            for line in split(r'(?<=[^0-9])(?<=[^a-z])[\.]', enter_line):
                candidates.append(line.strip(' ').strip('.').strip('\t'))

        self.sentences = []
        index = 0
        for candidate in candidates:
            if len(candidate) >= 1 and candidate not in dup:
                dup[candidate] = True
                self.sentences.append(Sentence(candidate + '.', index))
                index += 1
            
        del dup
        del candidates
    
    def _extract_nouns(self):
        okt = Okt()
        self.nouns = []
        self.stopwords = ["아", "휴", "아이구", "아이쿠", "아이고", "어", "나", "우리", "저희", "따라", "의해", "을", "를", "에", "의", "가",]
        
        for sentence in self.sentences:
            if sentence.text is not '':
                self.nouns.append(' '.join([noun for noun in okt.nouns(str(sentence.text))
                if noun not in self.stopwords and len(noun) > 1]))

    def _build_graph(self):
        #문장 그래프 처리
        self.graph = Graph()
        self.graph.add_nodes_from(self.sentences)
        #문장간의 모든 경우에서 유사도 탐색
        for sent1, sent2 in combinations(self.sentences, 2):
            weight = self._jaccard(sent1, sent2)
            if weight:
                self.graph.add_edge(sent1, sent2, weight=weight)
        
        #단어 그래프 처리
        self.tfidf = TfidfVectorizer()
        self.cnt_vec = CountVectorizer()
        cnt_vec_mat = normalize(self.cnt_vec.fit_transform(self.nouns).toarray().astype(float), axis=0)
        vocab = self.cnt_vec.vocabulary_
        self.words_graph = np.dot(cnt_vec_mat.T, cnt_vec_mat)
        self.idx2word = {vocab[word] : word for word in vocab}

    def _jaccard(self, sent1, sent2):
        p = sum((sent1.bow & sent2.bow).values())
        q = sum((sent1.bow | sent2.bow).values())
        return p / q if q else 0

    def get_word_ranks(self, graph, d=0.85):
        A = graph
        matrix_size = A.shape[0]
        for id in range(matrix_size):
            A[id, id] = 0 # diagonal 부분을 0으로
            link_sum = np.sum(A[:,id]) # A[:, id] = A[:][id]
            if link_sum != 0:
                A[:, id] /= link_sum
            A[:, id] *= -d
            A[id, id] = 1
        B = (1-d) * np.ones((matrix_size, 1))
        ranks = np.linalg.solve(A, B) # 연립방정식 Ax = b
        return {idx: r[0] for idx, r in enumerate(ranks)}

    def summarize(self, count=3, verbose=True):
        results = sorted(self.reordered[:count], key=lambda sentence: sentence.index)
        results = [result.text for result in results]
        if verbose:
            return '\n'.join(results)
        else:
            return results
