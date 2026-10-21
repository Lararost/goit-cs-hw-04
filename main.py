"""Запуск і порівняння двох реалізацій на однакових файлах."""
import multiprocessing as mp
from common import run_cli
from threading_search import search_threading
from multiprocessing_search import search_multiprocessing

if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(run_cli({"threading": search_threading,
                             "multiprocessing": search_multiprocessing}))
