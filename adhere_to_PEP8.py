#!/usr/bin/python
import os
import re


class AdhereToPEP8:
    def __init__(self):
        self._current_path = os.path.dirname(__file__)
        self.py_files_list = []
        self.file_data = ''
        self.alternative_import_strings = {
            'import cStringIO as StringIO\n':
                'try:\n\timport io as StringIO\nexcept ImportError:\n\timport cStringIO as StringIO',
            'import dircache\n':
                'try:\n\timport os as dircache\nexcept ImportError:\n\timport dircache',
            'import urlparse\n':
                'try:\n\tfrom urllib import parse as urlparse  # Python 3\n'
                'except ImportError:\n\timport urlparse  # Python 2.7',
            'import urllib2\n':
                'try:\n\tfrom urllib import request as urllib2\n'
                'except ImportError:\n\timport urllib2',
            'import cStringIO\n':
                'try:\n\tfrom io import StringIO as cStringIO\n'
                'except ImportError:\n\timport cStringIO as StringIO',
            'from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer\n':
                'try:\n\tfrom http.server import BaseHTTPRequestHandler, HTTPServer\n'
                'except ImportError:\n\tfrom BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer'
        }

    def find_py_files(self):
        for py_file in self.follow_rabbit(self._current_path):
            if py_file.endswith('.py') and py_file not in __file__:
                self.py_files_list.append(py_file)

    # scan current path and return all files recursively
    def follow_rabbit(self, trinity):
        for neo in os.scandir(trinity):
            # make sure to exclude virtualenv (venv in this case) and hidden folders
            if neo.is_dir(follow_symlinks=False) and not neo.name == 'venv' and not neo.name.startswith('.'):
                yield from self.follow_rabbit(neo.path)
            else:
                yield neo.path
    '''
    ref https://www.python.org/dev/peps/pep-0008/
    Use the function naming rules: lowercase with words separated by underscores as necessary to improve readability.
    Use one leading underscore only for non-public methods and instance variables.
    '''
    def bring_code_to_future(self, file):
        with open(file, 'r') as f:
            self.file_data = f.read()
        # print(f'search through {os.path.basename(file)}')
        for line in self.file_data.split('\n'):
            # check for python 2 imports and replace with try for python3 imports
            self.alternative_imports(line)
            # check for camel case method names and replace with kebab case
            self.convert_to_pep8(line)
            # check for class names with underscores and replace with camel case
            self.remove_underscore_from_class_name(line)

        # write changed data back into the same file.
        with open(filename, 'w') as f:
            f.write(self.file_data)

    def convert_to_pep8(self, line):
        match = re.search(r'def\s[A-Z].*\(', line)
        if match and not '__init__' in match.group():
            wrong_method = self.format_regex_object(match)
            # change first capital letter in method name to lower case
            correct_method = re.sub(r'^[A-Z]', self.to_lower, wrong_method)
            # handle 2 or more letters like CSV or GET first
            while re.search('[A-Z?*].[^a-z]', correct_method):
                correct_method = re.sub('[A-Z?*].[^a-z]', self.dash_and_lower, correct_method)
            # replace the rest of capital letters with _<lowercase>
            while not correct_method.islower():
                correct_method = re.sub('[A-Z]', self.dash_and_lower, correct_method)
            self.replace_in_file(wrong_method, correct_method)
            self.replace_in_project(wrong_method, correct_method)

    def remove_underscore_from_class_name(self, line):
        match = re.search(r'class\s[A-Z].*_[a-z].*\(', line)
        if match:
            wrong_class = self.format_regex_object(match)
            correct_class = re.sub(r'_[a-z]', self.without_dash_and_upper, wrong_class)
            self.replace_in_file(wrong_class, correct_class)
            self.replace_in_project(wrong_class, correct_class)

    def alternative_imports(self, line):
        if line in self.alternative_import_strings.keys():
            self.replace_in_file(line, self.alternative_import_strings[line])

    def replace_in_file(self, wrong, correct):
        self.file_data.replace(wrong, correct)

    @staticmethod
    def replace_in_project(wrong, correct):
        # replace all occurrences in the project
        cmd = f"""for f in $(find ./ -type f |grep -Ev 'venv|.git');do sed -i 's/{wrong}/{correct}/g' $f;done"""
        os.system(cmd)

    @staticmethod
    def without_dash_and_upper(match):
        return match.group().replace('_', '').upper()

    @staticmethod
    def to_lower(match):
        return match.group().lower()

    @staticmethod
    def dash_and_lower(match):
        return f'_{match.group().lower()}'

    @staticmethod
    def format_regex_object(match):
        return match.group().split(' ')[1].rstrip('(')


if __name__ == '__main__':
    fix_names = AdhereToPEP8()
    fix_names.find_py_files()
    for filename in fix_names.py_files_list:
        fix_names.bring_code_to_future(filename)
