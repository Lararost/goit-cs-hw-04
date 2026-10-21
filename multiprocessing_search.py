"""Багатопроцесорна версія із spawn та multiprocessing.Queue."""
import multiprocessing as mp
from queue import Empty
from common import prepare, scan_files, merge_results, run_cli


def _worker(index, files, keywords, queue):
    """Функція верхнього рівня сумісна зі spawn на macOS/Windows."""
    try:
        result, errors = scan_files(files, keywords)
        queue.put((index, result, errors, None))
    except Exception as exc:
        queue.put((index, None, [], f"{type(exc).__name__}: {exc}"))


def search_multiprocessing(files, keywords, workers=4):
    """Повернути dict; читати Queue до join, щоб не блокувати великі відповіді."""
    words, chunks = prepare(files, keywords, workers)
    if not chunks:
        return {word: [] for word in words}
    context = mp.get_context("spawn")
    queue = context.Queue()
    processes = [context.Process(target=_worker, args=(i, chunk, words, queue))
                 for i, chunk in enumerate(chunks)]
    started = []
    partials = {}
    try:
        for process in processes:
            process.start()
            started.append(process)
        while len(partials) < len(processes):
            try:
                index, result, errors, failure = queue.get(timeout=1)
            except Empty:
                failed = [p for p in started if p.exitcode not in (None, 0)]
                if failed:
                    raise RuntimeError(f"Процес завершився з кодом {failed[0].exitcode}.")
                if all(p.exitcode is not None for p in started):
                    raise RuntimeError("Процеси завершилися без усіх результатів.")
                continue
            if failure:
                raise RuntimeError(f"Помилка процесу {index}: {failure}")
            partials[index] = (result, errors)
        for process in started:
            process.join()
        if any(p.exitcode != 0 for p in started):
            raise RuntimeError("Один із процесів завершився аварійно.")
        return merge_results(words, [partials[i] for i in range(len(chunks))])
    finally:
        for process in started:
            if process.is_alive():
                process.terminate()
            process.join()
        queue.close()
        queue.join_thread()


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(run_cli({"multiprocessing": search_multiprocessing}))
