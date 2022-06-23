#!/usr/bin/env python3

import subprocess
import io
import sys
from ja.log import log

def run_cmake(argv, verbose):
	cmd = ['cmake'] + argv
	log('$ ' + ' '.join(cmd), True)
	if verbose:
		proc = subprocess.Popen(cmd)
	else:
		proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

		previous_line = ''
		color = ''

		for line in io.TextIOWrapper(proc.stdout, encoding='utf-8'):
			if len(previous_line) > 0 and line.startswith(previous_line):
				status = line[len(previous_line):].strip()
				if status.startswith('- '):
					status = status[2:]
				if status.startswith('-- '):
					status = status[3:]
				result_color = '\x1b[1;34m'
				if status == 'works' or status == 'found' or status == 'Success' or status == 'yes' or status == 'TRUE':
					result_color = '\x1b[1;32m'
				if status == 'Failed' or status == 'failed' or status == 'not found' or status == 'no' or status == 'NOTFOUND':
					result_color = '\x1b[1;31m'
				print(': {}{}\x1b[0m\n'.format(result_color, status), end='', flush=True)
				previous_line = ''
			else:
				line = line.rstrip()
				if previous_line != '':
					print('')
				if line == '':
					print('')
				elif not line.startswith('  '): # for indented lines, keep the previous color
					color = ''
				previous_line = line
				if line.startswith('-- '):
					line = '▸' + line[2:]
					# color = '\x1b[1m'
				if line.startswith('Failed to ') or line.startswith('CMake Error'):
					color = '\x1b[31m'
				if line.startswith('CMake Warning ') or line.startswith('Could NOT ') or \
				line.startswith('CMake Deprecation Warning'):
					color = '\x1b[33m'
				if line.startswith(' * '):
					line = ' • ' + line[3:]
				line_parts = line.split(': ')
				front = ': '.join(line_parts[:-1])
				back = line_parts[-1:][0]
				if len(line_parts) > 1 and front.count('(') == front.count(')'):
					print('{}{}: \x1b[1m{}\x1b[0m'.format(color, front, back), end='', flush=True)
				else:
					print('{}{}\x1b[0m'.format(color, line), end='', flush=True)

		if previous_line != '':
			print('')

	proc.wait() # sets returncode, shouldn't block
	if proc.returncode != 0:
		exit(proc.returncode)
