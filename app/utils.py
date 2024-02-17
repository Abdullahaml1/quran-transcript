import streamlit as st
from typing import Any


class MultiSelectSave(object):
    def __init__(self,
                 dict_obj: dict,
                 key_name: str,
                 max_len: int):
        self.key_name = key_name
        self.dict_obj = dict_obj
        self.max_len = max_len

    def __len__(self):
        return self.max_len

    def __getitem__(self, idx):
        key = f'{self.key_name}_{idx}'
        assert idx <= self.max_len, \
            f'Index out of range: max_len={self.max_len} you give: {idx}'

        assert key in self.dict_obj.keys(), \
            f'the key({key}) not in the dict_obj'
        return self.dict_obj[key]

    def __setitem__(self, idx, val):
        key = f'{self.key_name}_{idx}'
        assert idx <= self.max_len, \
            f'Index out of range: max_len={self.max_len} you give: {idx}'

        assert key in self.dict_obj.keys(), \
            f'the key({key}) not in the dict_obj'
        self.dict_obj[key] = val

    # # for looping
    # def __iter__(self):
    #     return self
    # and
    # def __next__(self):
    # src: https://www.programiz.com/python-programming/iterator

    def __iter__(self):
        for idx in range(self.max_len):
            yield self.__getitem__(idx).copy()



def edit_ayah_page(uthmani_words: list[str],
                   emlaey_words: list[str],
                   emlaey_to_uthmani: dict[str, str] = None) -> dict[str, str]:
    """
    the display function that maps emlaey script words to uthmani script words
    Args:
        uthmani_words: list[str] list of the uthmani words of the ayah
        emaley_words: list[str] list of the emlaey words of the ayah
        emaley_to_uthmani: dict[str, str] dict with
            keys (emaley words or words) and value of (uthmani word or words)
    Return:
        emaley_to_uthmani: dict[str, str] dict with
            keys (emaley words or words) and value of (uthmani word or words)
            after uditing using the User Interface
    """
    buttons_names = ['Edit', 'Fill', 'Clear']
    buttons = {}
    for col, button in zip(st.columns(len(buttons_names)), buttons_names):
        with col:
            buttons[button] = st.button(button)


def flatten(L: list):
    flattened_list = []
    for outer in L:
        for inner in outer:
            flattened_list.append(inner)
    return flattened_list


def convert_ids_to_options(ids: list[int],
                           options: list[Any]) -> list[Any]:
    return_options = []
    for idx in ids:
        return_options.append(options[idx])
    return return_options


def multiselect_callback(m_select_idx: int,
                         m_save_obj: MultiSelectSave,
                         multiselect='multiselect',
                         ):
    # we assuem to deselct or select only one box at a time
    if not st.session_state[f'{multiselect}_{m_select_idx}']:
        # move the box to the multiselct box above
        box_idx = m_save_obj[m_select_idx]['value']
        for key in ['value', 'options']:
            m_save_obj[m_select_idx - 1][key] += box_idx
            m_save_obj[m_select_idx - 1][key].sort()

        # ----------------------------------------------------------------
        # move all boxes down up one box starting of the selected box
        # ----------------------------------------------------------------
        for idx in range(m_select_idx, len(m_save_obj) - 2, 1):
            for key in ['value', 'options']:
                m_save_obj[idx][key] = m_save_obj[idx + 1][key]

        # box(N) - 2
        N = len(m_save_obj)
        for key in ['value', 'options']:
            m_save_obj[N - 2][key] = m_save_obj[N - 1]['value']

        # last box(N) - 1
        m_save_obj[N - 1]['options'] = sorted(
            set(m_save_obj[N - 1]['options']) - set(m_save_obj[N - 1]['value']))
        m_save_obj[N - 1]['value'] = m_save_obj[N - 1]['options'][:1]


def multiselect_list(options: list,
                     max_len: int):

    multiselect_save = 'multiselect_save'
    multiselect = 'multiselect'
    m_save_obj = MultiSelectSave(st.session_state, multiselect_save, max_len)

    # initialize sessoin state
    for m_idx in range(max_len - 1):
        if f'{multiselect_save}_{m_idx}' not in st.session_state:
            st.session_state[f'{multiselect_save}_{m_idx}'] = {
                'value': [m_idx],
                'options': [m_idx]
            }
            # value os the mulitselect box itself
            st.session_state[f'{multiselect}_{m_idx}'] = convert_ids_to_options(
                [m_idx], options)

    # last multiselct cell (filled with the rest of the cells)
    if f'{multiselect_save}_{max_len - 1}' not in st.session_state:
        st.session_state[f'{multiselect_save}_{max_len - 1}'] = {
            'value': [max_len - 1],
            'options': list(range(max_len - 1, len(options), 1))
        }
        # value os the mulitselect box itself
        st.session_state[f'{multiselect}_{max_len - 1}'] = convert_ids_to_options(
            [max_len - 1], options)

    # main code
    for m_idx in range(max_len):
        st.multiselect(
            options=convert_ids_to_options(
                m_save_obj[m_idx]['options'], options),
            default=convert_ids_to_options(
                m_save_obj[m_idx]['value'], options),
            label='Select',
            label_visibility='hidden',
            on_change=multiselect_callback,
            args=(m_idx, m_save_obj),
            key=f'{multiselect}_{m_idx}')
