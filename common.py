"""Спільна логіка пошуку: UTF-8, без урахування регістру, пошук підрядка."""
import argparse
import json
from pathlib import Path
import sys
from time import perf_counter


def prepare(files, keywords, workers):
    """Перевірити аргументи, прибрати дублікати та розподілити файли."""
    if isinstance(workers, bool) or not isinstance(workers, int) or workers < 1:
        raise ValueError("Кількість workers має бути додатним цілим числом.")
    words = list(dict.fromkeys(keywords))
    if not words or any(not isinstance(w, str) or not w.strip() for w in words):
        raise ValueError("Вкажіть хоча б одне непорожнє ключове слово.")
    paths = list(dict.fromkeys(str(Path(p)) for p in files))
    count = min(workers, len(paths))
    chunks = [paths[i::count] for i in range(count)]
    return words, chunks


def scan_files(files, keywords):
    """Повернути локальний словник і помилки, не перериваючи інші файли.

    Кожен файл читається повністю, тому підрядок може містити перенос рядка.
    Непридатний UTF-8 не ігнорується: такий файл потрапляє у список помилок.
    """
    result = {word: [] for word in keywords}
    errors = []
    for filename in files:
        try:
            content = Path(filename).read_text(encoding="utf-8-sig").casefold()
        except (OSError, UnicodeError) as exc:
            errors.append(f"{filename}: {type(exc).__name__}: {exc}")
            continue
        for word in keywords:
            if word.casefold() in content:
                result[word].append(filename)
    return result, errors


def merge_results(keywords, partials):
    """Об'єднати результати без повторів, стабільно відсортувати шляхи."""
    result = {word: [] for word in keywords}
    errors = []
    for partial, failures in partials:
        errors.extend(failures)
        for word in keywords:
            result[word].extend(partial[word])
    for word in result:
        result[word] = sorted(set(result[word]))
    for error in sorted(errors):
        print("Помилка читання:", error, file=sys.stderr)
    return result


def parser():
    p = argparse.ArgumentParser(description="Паралельний пошук підрядків у UTF-8 текстах.")
    p.add_argument("--directory", type=Path, default=Path(__file__).parent / "sample_texts")
    p.add_argument("--keywords", nargs="+", default=["python", "паралелізм", "docker"])
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--output", type=Path, help="Зберегти результат і час у JSON")
    return p


def discover(directory):
    """Рекурсивно знайти .txt; помилки доступу повідомляє викликач."""
    if not directory.is_dir():
        raise ValueError(f"Папку не знайдено: {directory}")
    # os.walk з onerror не приховує помилки доступу до вкладених папок.
    import os
    files = []
    def onerror(exc):
        raise exc
    for base, dirs, names in os.walk(directory, onerror=onerror):
        dirs.sort()
        files.extend(str(Path(base) / n) for n in sorted(names) if n.lower().endswith(".txt"))
    return sorted(files)


def run_cli(implementations):
    args = parser().parse_args()
    try:
        files = discover(args.directory)
        print(f"Знайдено текстових файлів: {len(files)}")
        runs = {}
        for label, search in implementations.items():
            start = perf_counter()
            result = search(files, args.keywords, args.workers)
            elapsed = perf_counter() - start
            runs[label] = {"seconds": elapsed, "results": result}
            print(f"\n{label}: {elapsed:.6f} с")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if len(runs) > 1:
            values = [r["results"] for r in runs.values()]
            if any(v != values[0] for v in values[1:]):
                raise RuntimeError("Результати реалізацій відрізняються.")
            print("\nРезультати обох реалізацій однакові.")
        if args.output:
            args.output.write_text(json.dumps(runs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Збережено: {args.output}")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Помилка: {exc}", file=sys.stderr)
        return 1
    return 0
