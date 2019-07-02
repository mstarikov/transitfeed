#!/usr/bin/python
import os
import re


def find_pyies():
    this_file_path = os.path.realpath(__file__)
    current_path = os.path.dirname(this_file_path)
    print(current_path)
    pyies_list = []
    for pyies in follow_rabbit(current_path):
        if pyies.endswith('.py') and not 'PEP8' in pyies:
            pyies_list.append(pyies)
    return pyies_list


def follow_rabbit(trinity):
    for neo in os.scandir(trinity):
        if neo.is_dir(follow_symlinks=False) and not neo.name == 'venv' and not neo.name.startswith('.'):
            yield from follow_rabbit(neo.path)
        else:
            yield neo.path


def convert_to_pep8(filename):
    with open(filename, 'r') as f:
        file_data = f.read()
    for line in file_data.split('\n'):
        match = re.search(r'def\s.*[A-Z].*\(', line)
        # match = re.search(rf'def+.*{pattern}\(', file_data)
        if match:
            if '__init__' in match.group():
                continue
            wrong_name = match.group().split(' ')[1].rstrip('(')
            function_name = re.sub(r'^[A-Z]', to_lower, wrong_name)
            while not function_name.islower():
                function_name = re.sub('[A-Z]', dash_and_lower, function_name)
            file_data = file_data.replace(wrong_name, function_name)
    with open(filename, 'w') as f:
        f.write(file_data)


def to_lower(match):
    return match.group().lower()


def dash_and_lower(match):
    return f'_{match.group().lower()}'


if __name__ == '__main__':
    file_list = find_pyies()
    for src in file_list:
        convert_to_pep8(src)
