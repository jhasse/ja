#!/usr/bin/env python3

import tempfile
import os
import subprocess

def run(cmd, should_fail=False):
	print('\x1b[1;36m$ ' + cmd + '\x1b[0m')
	try:
		subprocess.check_call(cmd, shell=True)
		if should_fail:
			raise Exception(cmd)
	except subprocess.CalledProcessError as err:
		if not should_fail:
			raise err

JA = 'PYTHONPATH=' + os.path.join(os.path.abspath(os.path.dirname(__file__))) + ' python3 -m ja'
with tempfile.TemporaryDirectory() as tdir:
	os.chdir(tdir)
	run(JA + ' --version')
	run(JA + ' --help')
	assert not os.listdir('.') # current directory should be empty
	with open('meson.build', 'w') as f:
		f.write("project('foo', 'c')\nexecutable('foo', 'main.c')")
	with open('main.c', 'w') as f:
		f.write('error')
	run(JA, True)
	assert not os.path.exists('build/ja.lock')
	run(JA + ' -t clean')
	assert not os.path.exists('build/ja.lock')
	run(JA + ' -t doesnt_exist', True)
	assert not os.path.exists('build/ja.lock')
	with open('main.c', 'w') as f:
		f.write("int main() {}")
	run(JA)
	assert os.path.exists('build/foo')
	run(JA + ' -t clean')
	assert not os.path.exists('build/foo')
	run(JA + ' -C build')
	assert os.path.exists('build/foo')
