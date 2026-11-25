"""Korean: Kiwi morphological analysis -> learnable words with candidate lemmas.

Rules (learned the hard way in kr-miner):
- Nouns + 하다/되다/스럽다 derivations become one word with the verb first: 무난하고 -> (무난하다, 무난).
- Noun suffixes that make a new word are kept (순차적, 사기꾼); grammatical ones (들, 님, 씨) are dropped.
- A prefix glued to a noun is a candidate too (맨손 -> 맨손, 손).
- Root words (XR) also get the 하다 form (깨끗 -> 깨끗하다).
- Adverbs ending in 게/히 also point at their adjective (이렇게 -> 이렇다, 조용히 -> 조용하다).
- Proper nouns, bound nouns, pronouns, numerals, interjections, determiners and lone single syllables are "weak":
  mostly names, fillers and mis-splits, they only count when the word list knows them.
- Particles, endings, punctuation, numbers and foreign script are not words to learn.
"""

from typing import cast

from kiwipiepy import Kiwi
from kiwipiepy import Token as KToken

from ..base import Token

VERBAL = {'VV': 'verb', 'VA': 'adjective', 'VX': 'verb'}
NOUNISH = {'NNG', 'XR'}
ADVERBISH = {'MAG', 'MAJ'}
WEAK = {'NNP', 'NNB', 'NP', 'NR', 'IC', 'MM'}
DERIV_SUFFIX = {'XSV', 'XSA'}
WORD_SUFFIX = {'적', '꾼', '질', '쟁이', '장이', '성', '화', '력', '감', '스럽'}
LEMMA_FIX = {'그다': '그렇다'}  # Kiwi lemma for the colloquial 그래 / 그런


def base_tag(tag: str) -> str:
    return tag.split('-', 1)[0]  # VV-R / VA-I -> VV / VA


Word = tuple[list[str], str, str, bool, tuple[str, ...]]  # lemmas, pos, key, weak, extra tags (consumed suffix)


class KoreanPack:
    code = 'ko'
    name = 'Korean'

    def __init__(self) -> None:
        self.kiwi = Kiwi()

    def analyze(self, text: str) -> list[Token]:
        return self._tokens(text, cast(list[KToken], self.kiwi.tokenize(text)))

    def analyze_many(self, texts: list[str]) -> list[list[Token]]:
        if not texts:
            return []
        batches = cast(list[list[KToken]], list(self.kiwi.tokenize(texts)))
        return [self._tokens(t, toks) for t, toks in zip(texts, batches, strict=True)]

    def _tokens(self, text: str, toks: list[KToken]) -> list[Token]:
        def eojeol(i: int) -> tuple[int, int]:
            s, e = i, i
            while s > 0 and not text[s - 1].isspace():
                s -= 1
            while e < len(text) and not text[e].isspace():
                e += 1
            while s < e and text[s] in '.,!?\'"…~([{「『':
                s += 1
            while e > s and text[e - 1] in '.,!?\'"…~)]}」』':
                e -= 1
            return s, e

        out: list[Token] = []
        i = 0
        while i < len(toks):
            t = toks[i]
            tag = base_tag(t.tag)
            nxt = toks[i + 1] if i + 1 < len(toks) else None
            prev = toks[i - 1] if i > 0 else None
            word = self._word(t, tag, prev, nxt)
            if word is not None:
                lemmas, pos, key, weak, extra = word
                if extra:
                    i += 1  # the derivation suffix (하다/되다) belongs to this word
                s, e = eojeol(t.start)
                uniq = tuple(dict.fromkeys(x for x in lemmas if x))
                if uniq and s < e:
                    out.append(Token(text[s:e], s, e, uniq, pos, key, weak, (t.tag, *extra)))
            i += 1
        return out

    @staticmethod
    def _word(t: KToken, tag: str, prev: KToken | None, nxt: KToken | None) -> Word | None:
        """What learnable word starts at Kiwi token `t` (None: particle, ending, punctuation...)."""
        if tag in WEAK:
            return [t.form, t.lemma or ''], 'other', t.form, True, ()
        if tag in NOUNISH:
            cands: list[str] = []
            noun = t.form
            extra: tuple[str, ...] = ()
            if prev is not None and prev.tag == 'XPN' and prev.end == t.start:
                cands.append(prev.form + noun)  # 맨+손
            if nxt is not None and nxt.start == t.end:
                if base_tag(nxt.tag) in DERIV_SUFFIX:  # 무난+하다
                    suf = nxt.lemma if nxt.lemma.endswith('다') else nxt.lemma + '다'
                    cands.insert(0, noun + suf)
                    extra = (nxt.tag,)
                elif nxt.tag == 'XSN' and nxt.form in WORD_SUFFIX:  # 순차+적
                    cands.insert(0, noun + nxt.form)
            cands.append(noun)
            if tag == 'XR':
                cands.append(noun + '하다')
            pos = 'verb' if extra and base_tag(extra[0]) == 'XSV' else 'adjective' if extra else 'noun'
            return cands, pos, noun, all(len(c) == 1 for c in cands), extra
        if tag in VERBAL:
            lemma = t.lemma or t.form + '다'
            lemma = LEMMA_FIX.get(lemma, lemma)
            return [lemma], VERBAL[tag], lemma, False, ()
        if tag in ADVERBISH:
            cands = [t.form]
            if t.form.endswith('게') and len(t.form) > 1:
                cands.append(t.form[:-1] + '다')
            elif t.form.endswith('히') and len(t.form) > 1:
                cands.append(t.form[:-1] + '하다')
            return cands, 'adverb', t.form, False, ()
        return None
