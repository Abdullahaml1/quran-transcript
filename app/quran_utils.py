from functools import reduce
import operator
from pathlib import Path
import json
import xmltodict
from dataclasses import dataclass
import re
from app import alphabet as alpha


def get_from_dict(data_dict: dict, keys: list[str]):
    """
    src: https://stackoverflow.com/questions/14692690/access-nested-dictionary-items-via-a-list-of-keys
    get a value from dict using sequence of keys
    Example:
        d = {'a': {'b': {'c': 3}}}
       get_from_dict(d, ['a', 'b', 'c'])
       >> 3
    """
    return reduce(operator.getitem, keys, data_dict)


class PartOfUthmaniWord(Exception):
    pass


@dataclass
class RasmFormat:
    uthmani: list[list[str]]
    imlaey: list[list[str]]


@dataclass
class Vertex:
    aya_idx: int
    word_idx: int


@dataclass
class WordSpan:
    start: int
    end: int


@dataclass
class AyaFormat:
    sura_idx: int
    aya_idx: int
    sura_name: str
    num_ayat_in_sura: int
    uthmani: str
    imlaey: str
    rasm_map: dict[str, list[str]] = None
    bismillah_uthmani: str = None
    bismillah_imlaey: str = None
    bismillah_map: dict[str, list[str]] = None

    def get_formatted_rasm_map(self,
                               join_prefix=' ',
                               uthmani_key='@uthmani',
                               imlaey_key='@imlaey',
                               ) -> RasmFormat:
        """
        return rasm map in fromt like:
            [
                {'@uthmani: str, '@imlaey: str},
                {'@uthmani: str, '@imlaey: str},
            ]
            to
            RasmFormat.uthmani: list[list[str]]
            RasmFormat.imlaey: list[list[str]]
        """
        if self.rasm_map is None:
            raise ValueError('Rasmp map is None')

        uthmani_words: list[list[str]] = []
        imlaey_words: list[list[str]] = []
        for item in self.rasm_map:
            uthmani_words.append(item[uthmani_key].split(join_prefix))
            imlaey_words.append(item[imlaey_key].split(join_prefix))
        return RasmFormat(
            uthmani=uthmani_words,
            imlaey=imlaey_words)


class Aya(object):
    def __init__(self, quran_path: str | Path,
                 sura_idx=1,
                 aya_idx=1,
                 quran_dict: dict = None,
                 prefix='@',
                 map_key='rasm_map',
                 bismillah_map_key='bismillah_map',
                 bismillah_key='bismillah',
                 uthmani_key='uthmani',
                 imlaey_key='imlaey',
                 sura_name_key='name',
                 join_prefix=' ',
                 ):
        """
        quran_path (str | Path) path to the quran json script with
            emlaey uthmani scripts
        sura_idx: the index of the Sura in the Quran starting with 1 to 114
        aya_idx: the index of the aya starting form 1
        """
        self.quran_path = Path(quran_path)
        if quran_dict is None:
            with open(self.quran_path, 'r', encoding='utf8') as f:
                self.quran_dict = json.load(f)
        else:
            self.quran_dict = quran_dict

        self._check_indices(sura_idx - 1, aya_idx - 1)
        self.sura_idx = sura_idx - 1
        self.aya_idx = aya_idx - 1

        self.map_key = map_key
        self.bismillah_map_key = bismillah_map_key
        self.uthmani_key = prefix + uthmani_key
        self.imlaey_key = prefix + imlaey_key
        self.sura_name_key = prefix + sura_name_key
        self.bismillah_uthmani_key = f'{prefix}{bismillah_key}_{uthmani_key}'
        self.bismillah_imlaey_key = f'{prefix}{bismillah_key}_{imlaey_key}'
        self.join_prefix = join_prefix

    def _get_sura(self, sura_idx):
        assert sura_idx >= 0 and sura_idx <= 113, (
            f'Wrong Sura index {sura_idx + 1}')
        return self.quran_dict['quran']['sura'][sura_idx]['aya']

    def _get_sura_object(self, sura_idx):
        assert sura_idx >= 0 and sura_idx <= 113, (
            f'Wrong Sura index {sura_idx + 1}')
        return self.quran_dict['quran']['sura'][sura_idx]

    def _get_aya(self, sura_idx, aya_idx):
        assert aya_idx >= 0 and aya_idx < len(self._get_sura(sura_idx)), (
            f'Sura index out of range sura_index={sura_idx + 1} ' +
            f'and len of sura={len(self._get_sura(sura_idx))}')
        return self._get_sura(sura_idx)[aya_idx]

    def _get(self, sura_idx, aya_idx) -> AyaFormat:
        """
        get an aya from quran script
        Args:
            sura_idx (int): from 0 to 113
            aya_idx (int): form 0 to len(sura) - 1
        Example to get the first aya of sura Alfateha quran_scirt[1, 1]
        Return:
            AyaFormt:
                sura_idx (int): the absoulte index of the sura
                aya_idx (int): the absoulte index of the aya
                sura_name (str): the name of the sura
                num_aya_in_sura (int): number of ayat in the sura
                uthmani (str): the uthmani script of the aya
                imlaey (str): the imlaey script of the aya

                rasm_map (list[dict[str, str]]): maping from imaley to uthmani
                    scritps (word of uthmani to word or words of imlaey) and the
                    opesite. Example:
                    rasm_map=[
                        {'@uthmani': 'مِنَ', '@imlaey': 'مِنَ'},
                        {'@uthmani': 'ٱلْجِنَّةِ', '@imlaey': 'الْجِنَّةِ'},
                        {'@uthmani': 'وَٱلنَّاسِ', '@imlaey': 'وَالنَّاسِ'}]
                    Every item in the item is a dict with "@uthmain" and
                    if None: the rasem map is not set yet

                bismillah_uthmani (str): bismillah in uthmani script if the
                    aya index == 1 and the sura has bismillah or bismillah is
                    not aya like sura Alfateha and else (None)

                bismillah_imlaey (str): bismillah in uthmani script if the
                    aya index == 1 and the sura has bismillah or bismillah is
                    not aya like sura Alfateha and else (None)

                bismillah_map (list[dict[str, str]]): maping from imaley to uthmani
                    scritps (word of uthmani to word or words of imlaey) and
                    the opesite. Example:
                    bismillah_map=[
                        {'@uthmani': 'بِسْمِ', '@imlaey': 'بِسْمِ'},
                        {'@uthmani': 'ٱللَّهِ', '@imlaey': 'اللَّهِ'},
                        {'@uthmani': 'ٱلرَّحْمَـٰنِ', '@imlaey': 'الرَّحْمَٰنِ'},
                        {'@uthmani': 'ٱلرَّحِيمِ', '@imlaey': 'الرَّحِيمِ'}]
                        Every item in the item is a dict with "@uthmain" and
                    if None: the aya is not the first aya of the sura
                    (Note: bismillah maping is set automaticllay no by the user)
        """
        bismillah = {self.bismillah_uthmani_key: None,
                     self.bismillah_imlaey_key: None}
        for key in bismillah.keys():
            if key in self._get_aya(sura_idx, aya_idx).keys():
                bismillah[key] = self._get_aya(sura_idx, aya_idx)[key]

        bismillah_map = None
        if self.bismillah_map_key in self._get_aya(sura_idx, aya_idx).keys():
            bismillah_map = self._get_aya(sura_idx, aya_idx)[
                self.bismillah_map_key]

        rasm_map = None
        if self.map_key in self._get_aya(sura_idx, aya_idx).keys():
            rasm_map = self._get_aya(sura_idx, aya_idx)[self.map_key]

        return AyaFormat(
            sura_idx=sura_idx + 1,
            aya_idx=aya_idx + 1,
            sura_name=self._get_sura_object(sura_idx)[self.sura_name_key],
            num_ayat_in_sura=len(self._get_sura(sura_idx)),
            uthmani=self._get_aya(sura_idx, aya_idx)[self.uthmani_key],
            imlaey=self._get_aya(sura_idx, aya_idx)[self.imlaey_key],
            rasm_map=rasm_map,
            bismillah_uthmani=bismillah[self.bismillah_uthmani_key],
            bismillah_imlaey=bismillah[self.bismillah_imlaey_key],
            bismillah_map=bismillah_map,
            )

    def get(self) -> AyaFormat:
        """
        get an aya from quran script
        Return:
            AyaFormt:
                sura_idx (int): the absoulte index of the sura
                aya_idx (int): the absoulte index of the aya
                sura_name (str): the name of the sura
                uthmani (str): the uthmani script of the aya
                imlaey (str): the imlaey script of the aya

                bismillah_uthmani (str): bismillah in uthmani script if the
                    aya index == 1 and the sura has bismillah or bismillah is
                    not aya like sura Alfateha and else (None)

                bismillah_imlaey (str): bismillah in uthmani script if the
                    aya index == 1 and the sura has bismillah or bismillah is
                    not aya like sura Alfateha and else (None)
        """

        return self._get(self.sura_idx, self.aya_idx)

    def __str__(self):
        return str(self.get())

    def _check_indices(self, sura_idx: int, aya_idx: int):
        """
        check sura ds compatibility
        """
        assert sura_idx >= 0 and sura_idx <= 113, (
            f'Wrong Sura index {sura_idx + 1}')

        assert aya_idx >= 0 and aya_idx < len(self._get_sura(sura_idx)), (
            f'Aya index out of range (sura_index={sura_idx + 1} ' +
            f'aya_index={aya_idx + 1}) ' +
            f'and length of sura={len(self._get_sura(sura_idx))}')

    def _set_ids(self, sura_idx, aya_idx):
        self.sura_idx = sura_idx
        self.aya_idx = aya_idx

    def set(self, sura_idx, aya_idx) -> None:
        """
        Set the aya
        Args:
        sura_idx: the index of the Sura in the Quran starting with 1 to 114
        aya_idx: the index of the aya starting form 1
        """
        self._check_indices(sura_idx - 1, aya_idx - 1)
        self._set_ids(sura_idx=sura_idx - 1, aya_idx=aya_idx - 1)

    def set_new(self, sura_idx, aya_idx):
        """
        Return new aya with sura, and aya indices
        Args:
        sura_idx: the index of the Sura in the Quran starting with 1 to 114
        aya_idx: the index of the aya starting form 1
        """
        return Aya(
            quran_path=self.quran_path,
            sura_idx=sura_idx,
            aya_idx=aya_idx,
            quran_dict=self.quran_dict,
        )

    def step(self, step_len: int):
        """
        Return new Aya object with "step_len" aya after of before
        """
        aya_relative_idx = step_len + self.aya_idx

        # +VE or zero aya idx
        if aya_relative_idx >= 0:
            sura_idx = self.sura_idx
            while True:
                num_ayat = self._get(
                    sura_idx=sura_idx, aya_idx=0).num_ayat_in_sura
                if (aya_relative_idx < num_ayat):
                    break
                aya_relative_idx -= num_ayat
                sura_idx = (sura_idx + 1) % 114

        # -VE aya idx
        else:
            sura_idx = (self.sura_idx - 1) % 114
            while True:
                num_ayat = self._get(
                    sura_idx=sura_idx, aya_idx=0).num_ayat_in_sura
                aya_relative_idx += num_ayat
                if (aya_relative_idx >= 0):
                    break

        return Aya(
            quran_path=self.quran_path,
            sura_idx=sura_idx + 1,
            aya_idx=aya_relative_idx + 1,
            quran_dict=self.quran_dict,
        )

    # TODO Add vertix
    def get_ayat_after(
        self,
        end_vertix=(114, 6),
        num_ayat=None
            ):
        """
        iterator looping over Quran ayayt (verses) starting from the
        current aya to the end of the Holy Quran
        Args:
            num_aya: loop for ayat until reaching aya + num_ayat - 1
        """
        if num_ayat is not None:
            aya = self
            for _ in range(num_ayat):
                yield aya
                aya = aya.step(1)
            return

        aya_start_idx = self.aya_idx
        for sura_loop_idx in range(self.sura_idx, 114):
            for aya_loop_idx in range(
                    aya_start_idx, len(self._get_sura(sura_loop_idx))):
                yield Aya(
                    quran_path=self.quran_path,
                    sura_idx=sura_loop_idx + 1,
                    aya_idx=aya_loop_idx + 1,
                    quran_dict=self.quran_dict,
                )
            aya_start_idx = 0

    def _get_map_dict(self,
                      uthmani_list: list[str],
                      imlaey_list: list[str]
                      ) -> dict[str, list[dict[str, str]]]:
        """
        Return:
            [
                {'@uthmani: str, '@imlaey: str},
                {'@uthmani: str, '@imlaey: str},
            ]
        """
        map_list: list[str] = []
        for uthmani_words, imlaey_words in zip(uthmani_list, imlaey_list):
            map_list.append(
                {
                    self.uthmani_key: self.join_prefix.join(uthmani_words),
                    self.imlaey_key: self.join_prefix.join(imlaey_words),
                })
        return map_list

    def _get_str_from_lists(self, L: list[list[str]]) -> str:
        """
        join a list of lists of str with (self.join_prefix)
        Example: :
            L = [
                    ['a', 'b'],
                    ['c', 'd', 'e']
                ]
            self.join_prefic = ' '
            Ouput: 'a b c d e'
        """
        return self.join_prefix.join([self.join_prefix.join(x) for x in L])

    def set_rasm_map(
        self,
        uthmani_list: list[list[str]],
        imlaey_list: list[list[str]],
            ):
        # Assert len
        assert len(uthmani_list) == len(imlaey_list), (
            f'Lenght mismatch: len(uthmani)={len(uthmani_list)} ' +
            f'and len(imlaey)={len(imlaey_list)}'
        )

        # assert missing script
        # (Uthmani)
        assert self._get_str_from_lists(uthmani_list) == self.get().uthmani, (
            f'Missing Uthmani script words! input_uthmani_list={uthmani_list}' +
            f'\nAnd the original uthmani Aya={self.get().uthmani}')
        # (Imlaey)
        assert self._get_str_from_lists(imlaey_list) == self.get().imlaey, (
            f'Missing Imlaey script words! input_imlaey_list={imlaey_list}' +
            f'\nAnd the original imlaey Aya={self.get().imlaey}')

        # check first aya (set bismillah map)
        bismillah_map = None
        if (self.get().bismillah_uthmani is not None and
                self.get().bismillah_map is None):
            bismillah_uthmani = self.get().bismillah_uthmani.split(self.join_prefix)
            bismillah_uthmani = [[word] for word in bismillah_uthmani]
            bismillah_imlaey = self.get().bismillah_imlaey.split(self.join_prefix)
            bismillah_imlaey = [[word] for word in bismillah_imlaey]

            bismillah_map = self._get_map_dict(
                uthmani_list=bismillah_uthmani,
                imlaey_list=bismillah_imlaey)

        # get rasm map
        rasm_map = self._get_map_dict(
            uthmani_list=uthmani_list,
            imlaey_list=imlaey_list)

        # save quran script file
        self.quran_dict['quran']['sura'][self.sura_idx]['aya'][self.aya_idx][
            self.map_key] = rasm_map
        if bismillah_map is not None:
            self.quran_dict['quran']['sura'][self.sura_idx]['aya'][self.aya_idx][
                self.bismillah_map_key] = bismillah_map

    def save_quran_dict(self):
        # save the file
        with open(self.quran_path, 'w+', encoding='utf8') as f:
            json.dump(self.quran_dict, f, ensure_ascii=False, indent=2)

        # # TODO for debuging
        # with open(self.quran_path.parent / 'text.xml', 'w+', encoding='utf8') as f:
        #     new_file = xmltodict.unparse(self.quran_dict, pretty=True)
        #     f.write(new_file)

    def get_formatted_rasm_map(self) -> RasmFormat:
        """
        return rasm map in fromt like:
            [
                {'@uthmani: str, '@imlaey: str},
                {'@uthmani: str, '@imlaey: str},
            ]
            to
            RasmFormat.uthmani: list[list[str]]
            RasmFormat.imlaey: list[list[str]]
        """
        if self.get().rasm_map is None:
            raise ValueError('Rasmp map is None')

        uthmani_words: list[list[str]] = []
        imlaey_words: list[list[str]] = []
        for item in self.get().rasm_map:
            uthmani_words.append(item[self.uthmani_key].split(self.join_prefix))
            imlaey_words.append(item[self.imlaey_key].split(self.join_prefix))
        return RasmFormat(
            uthmani=uthmani_words,
            imlaey=imlaey_words)

    # TODO: add end word span == None (rest of Aya)
    def imlaey_to_uthmani(self, imlaey_word_span: WordSpan) -> str:
        """
        return the uthmai script of the given imlaey script represented by
        the imlaey wordspand
        """
        imlaey2uthmani: dict[int, int] = self._encode_imlaey_to_uthmani()
        uthmani_script = self._decode_uthmani(
            imlaey2uthmani=imlaey2uthmani, imlaey_wordspan=imlaey_word_span)
        return uthmani_script

    def _encode_imlaey_to_uthmani(self) -> dict[int, int]:
        uthmani_words = self.get().uthmani.split(self.join_prefix)
        imlaey_words = self.get().imlaey.split(self.join_prefix)

        if len(uthmani_words) == len(imlaey_words):
            return {idx: idx for idx in range(len(uthmani_words))}

        # len mismatch
        iml_idx = 0
        imlaey2uthmani = {}
        for uth_idx in range(len(uthmani_words)):

            # special words of Uthmani Rasm
            span = self._get_unique_rasm_map_span(iml_idx, imlaey_words)
            if span is not None:
                for idx in range(iml_idx, iml_idx + span):
                    imlaey2uthmani[idx] = uth_idx
                iml_idx += span

            elif imlaey_words[iml_idx] in alpha.unique_rasm.imlaey_starts:
                imlaey2uthmani[iml_idx] = uth_idx
                imlaey2uthmani[iml_idx + 1] = uth_idx
                iml_idx += 2

            else:
                imlaey2uthmani[iml_idx] = uth_idx
                iml_idx += 1

        assert sorted(imlaey2uthmani.keys())[-1] == len(self.get().imlaey.split(self.join_prefix)) - 1

        assert sorted(imlaey2uthmani.values())[-1] == len(self.get().uthmani.split(self.join_prefix)) - 1

        return imlaey2uthmani

    def _get_unique_rasm_map_span(self, idx: int, words: list[int]) -> int:
        """
        check that words starting of idx is in alphabet.unique_rasm.rasm_map
        if that applies, it will return the number of imlaey words in
        alphabet.unique_rasm.rasm_map
        Else: None
        """
        for unique_rasm in alpha.unique_rasm.rasm_map:
            span = len(unique_rasm['imlaey'].split(self.join_prefix))
            if (self.join_prefix.join(words[idx: idx + span]) ==
                    unique_rasm['imlaey']):
                return span
        return None

    def _decode_uthmani(
        self,
        imlaey2uthmani: dict[int, int],
        imlaey_wordspan: WordSpan,
            ) -> str:
        """
        return the uthmani script of the given imlaey_word_span in
        Imlaey script Aya
        """
        if imlaey_wordspan.end in imlaey2uthmani.keys():
            if (imlaey2uthmani[imlaey_wordspan.end - 1] ==
                    imlaey2uthmani[imlaey_wordspan.end]):
                raise PartOfUthmaniWord(
                    'The Imlay Word is part of uthmani word')

        out_script = ""
        prev_uth_idx = -1
        uthmani_words = self.get().uthmani.split(self.join_prefix)
        for idx in range(imlaey_wordspan.start, imlaey_wordspan.end):
            if prev_uth_idx != imlaey2uthmani[idx]:
                out_script += uthmani_words[imlaey2uthmani[idx]]

                # Adding space Except for end idx
                if idx != imlaey_wordspan.end - 1:
                    out_script += self.join_prefix
            prev_uth_idx = imlaey2uthmani[idx]
        return out_script


@dataclass
class SearchItem:
    start_aya: Aya
    num_ayat: int
    imlaey_word_span: WordSpan
    uthmani_script: int
    has_bismillah: bool = False
    """
    start_aya (Aya): the start aya
    num_aya: (int): number of ayat that is included in the search item
    has_bismillah: True if the search item has bismliilah
        (not the Aya in El-Fatiha of in the Alnaml)
    imlaey_word_span (WordSpan):
        start: the start word idx of the imlaey scriptin thestart_aya
        end: the end imlaey_idx of the imlaey (start_aya + num_ayat - 1)
    uthmani_script (str) the equvilent uthmani script of the given imlaey script
    """


# TODO add:
# *. window
# *. include_bismillah
def search(
    start_aya: Aya,
    text: str,
    window: int = 1,
    include_bismillah=True,
    suffix=' ',
    **kwargs,
        ) -> list[SearchItem]:
    """
    searches the Holy Quran of Imlaey script to match the given text
    Args:
        start_aya (Aya): the start aya with which we loop throw the Holly Quran ayat
        text (str): the text to search with (expected with imlaey script)
        suffix (str): the suffix that sperate the quran words either imlaey or uthmani
        the rest of **kwargs are from normalize_aya function
    Return:
        list[[tuple(WordSpan, Aya]]
        every item has:
            WordSpan: the start_word_idx and end_word_idx + 1 word in
                the imlaey script in the aya
            Aya: the aya object the search was found for
    """
    normalized_text: str = normalize_aya(
        text,
        remove_spaces=True,
        **kwargs)

    found = []
    # Prepare ayat within winodw [-window/2: window/2]
    loop_aya = start_aya.step(-window // 2)
    aya_imlaey_words: list[list[str]] = []
    aya_imlaey_str = ""
    for aya in loop_aya.get_ayat_after(num_ayat=window + 1):
        aya_words = normalize_aya(
            aya.get().imlaey,
            remove_spaces=False,
            **kwargs,
        ).split(suffix)
        aya_imlaey_words.append(aya_words)

        aya_imlaey: str = normalize_aya(
            aya.get().imlaey,
            remove_spaces=True,
            **kwargs)
        aya_imlaey_str += aya_imlaey

    for re_search in re.finditer(normalized_text, aya_imlaey):
        if re_search is not None:
            start_vertex, end_vertex = get_words_span(
                start=re_search.span()[0],
                end=re_search.span()[1],
                words=aya_imlaey_words)
            found.append(SearchItem(
                start_aya=loop_aya.step(start_vertex.aya_idx),
                num_ayat=end_vertex.aya_idx - start_vertex.aya_idx + 1,
                imlaey_word_span=WordSpan(start=start_vertex.word_idx, end=end_vertex.word_idx),
                has_bismillah=False,
                uthmani_script=""))
    return found


def normalize_aya(
    text: str,
    remove_spaces=True,
    ignore_hamazat=False,
    ignore_alef_maksoora=True,
    ignore_haa_motatrefa=False,
    ignore_taa_marboota=False,
    ignore_small_alef=True,
    ignore_tashkeel=False,
        ) -> str:
    norm_text = text

    # TODO Ingonre alef as hamza

    if remove_spaces:
        norm_text = re.sub(r'\s+', '', norm_text)

    if ignore_alef_maksoora:
        norm_text = re.sub(
            alpha.imlaey.alef_maksoora,
            alpha.imlaey.alef, norm_text)

    if ignore_hamazat:
        norm_text = re.sub(
            f'[{alpha.imlaey.hamazat}]',
            alpha.imlaey.hamza,
            norm_text)

    if ignore_haa_motatrefa:
        norm_text = re.sub(
            f'[{alpha.imlaey.taa_marboota + alpha.imlaey.haa}]',
            alpha.imlaey.haa,
            norm_text)

    if ignore_taa_marboota:
        norm_text = re.sub(
            f'[{alpha.imlaey.taa_mabsoota + alpha.imlaey.taa_marboota}]',
            alpha.imlaey.taa_mabsoota,
            norm_text)

    if ignore_small_alef:
        norm_text = re.sub(
            alpha.imlaey.small_alef, '', norm_text)

    if ignore_tashkeel:
        norm_text = re.sub(
            f'[{alpha.imlaey.tashkeel}]', '', norm_text)

    return norm_text


def get_words_span(start: int, end: int, words_list=list[list[str]]
                   ) -> tuple[Vertex, Vertex]:
    """
    return the word indices at every word boundary only not inside the word:
    which means:
    * start character is at the beginning of the word
    * end character is at the end of the word + 1
    EX: start = 0, end = 8, words_list=[['aaa', 'bbb',], ['cc', 'ddd']]
                                          ^                 ^
                                          0               8 - 1
    return (start, end)
    (start.aya_idx=0, start.word_idx=0, end. aya_idx=1, end.word_idx=0 + 1)

    return None (start not at the beginning of the word) or
        (end is not at (end + 1) of the word)

    Args:
        start (int): the start char idx
        end (int): the end char idx + 1
        words_list (list[list[str]]): given words

    return: WordSpan:
        start: the start idx of the word in "words"
        end: (end_idx + 1) of the word in "words"
        if valid boundary else None
    """
    def _get_start_span(start_char: int) -> tuple[int, int]:
        chars_count = 0
        for aya_idx in range(len(words_list)):
            for word_idx in range(len(words_list[aya_idx])):
                if start_char == chars_count:
                    return aya_idx, word_idx
                chars_count += len(words_list[aya_idx][word_idx])
            aya_idx += 1
        return None

    def _get_end_span(
            end_char: int, chars_count=0,
            start_aya_idx=0, start_word_idx=0) -> tuple[int, int]:
        for aya_idx in range(start_aya_idx, len(words_list)):
            for word_idx in range(start_word_idx, len(words_list[aya_idx])):
                chars_count += len(words_list[aya_idx][word_idx])
                if end_char == chars_count:
                    return aya_idx, word_idx + 1
            start_word_idx = 0
        return None

    span = _get_start_span(start)
    # print(f'start=({span})')
    if span is None:
        return None
    start_aya_idx, start_word_idx = span

    span = _get_end_span(end,
                         chars_count=start,
                         start_aya_idx=start_aya_idx,
                         start_word_idx=start_word_idx)
    # print(f'end=({span})')
    if span is None:
        return None
    end_aya_idx, end_word_idx = span
    return (Vertex(aya_idx=start_aya_idx, word_idx=start_word_idx),
            Vertex(aya_idx=end_aya_idx, word_idx=end_word_idx))
