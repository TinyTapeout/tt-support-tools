'''
	TruthTable testing
	Copyright (C) 2023 Pat Deegan, https://psychogenic.com

	A simple system to take truth table data from yosys, like

		 ui_in  | uo_out
	 ---------- | -----------
	 8'11111000 | 8'xxxxxxx0
	 8'11111001 | 8'xxxxxxx1
	 8'11111010 | 8'xxxxxxx0
	 ...
    
    or manually crafted combi- or clocked sequences, encapsulated in 
    markdown tables such as

    |IN:  CBA  RC  |    output    | comment   |
    |--------------|--------------|-----------|
    | --- ---  1c  | -- ----- -   | reset     |
    | --- ---  0c  | -- ----- -   |           |
    | --- 111  -c  | -- 11100 -   |           |
    | --- 110  -c  | -- 11111 -   | success   |
    | --- 000  tc  | -- ----- -   | reset     |
    | --- ---  tc  | -- 11100 -   | locked    |
    ...

	and run it through cocotb harness.
	
    SAMPLE USAGE:

	@cocotb.test()
	async def truthTableCompare(dut):
		i_bus = dut.ui_in
		o_bus = dut.uo_out
		tt = truthtable.loadSimpleTruthTable('test/truthtable.txt')
		await tt.testAll(i_bus, o_bus, dut._log)
		

   SPDX-FileCopyrightText: © 2023 Pat Deegan, https://psychogenic.com
   SPDX-License-Identifier: Apache2.0
'''

from string import Template as StringTemplate
from cocotb.triggers import Timer
from cocotb.binary import BinaryValue
from enum import Enum
import re
import logging 

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class BitValue(Enum):
	DigitalLow = 0 
	DigitalHigh = 1
	Toggle = 2
	Clock = 3
	NoAction = 4
	
	@classmethod 
	def fromString(cls, v:str):
		mapping = {
				'x': BitValue.NoAction,
				'-': BitValue.NoAction,
				'0': BitValue.DigitalLow,
				'1': BitValue.DigitalHigh,
				't': BitValue.Toggle,
				'c': BitValue.Clock
			}
		if v.lower() in mapping:
			return mapping[v.lower()]
		
		return BitValue.NoAction

	
	@classmethod 
	def isDigitalValue(cls, val):
		if val == BitValue.DigitalLow or val == BitValue.DigitalHigh:
			return True 
		return False
	
	@classmethod 
	def toString(cls, v):
		mapping = {
			BitValue.NoAction: '-',
			BitValue.DigitalLow: '0',
			BitValue.DigitalHigh: '1',
			BitValue.Clock: 'c',
			BitValue.Toggle: 't'
			}
		if v in mapping:
			return mapping[v]
		return str(v)
class SaneBinaryValue(BinaryValue):
	def __init__(self, vstr:str):
		
		
		if type(vstr) == list:
			elements = []
			for v in vstr:
				elements.append(BitValue.toString(v))
			
			vstr = ''.join(elements)
			
		super().__init__(vstr, n_bits=len(vstr), bigEndian=False)
		numbits = len(vstr)
		self.hardBit = [True]*numbits
		for i in range(numbits):
			c = vstr[i]
			if c != '1' and c != '0' \
				and c!= BitValue.DigitalLow and c != BitValue.DigitalHigh:
				self.hardBit[(numbits - 1) - i] = False



class TestStep:
	def __init__(self, nReset:str, clock:str, inputs:str, outputs:str='', comment:str=''):
		self.nReset = BitValue.fromString(nReset)
		self.clock = BitValue.fromString(clock)
		self.inputs = list(map(BitValue.fromString, inputs))
		if len(outputs):
			self.outputs = list(map(BitValue.fromString, outputs))
		else:
			self.outputs = []
		
		self.numClockingActions = 0
		self.comment = comment
		self._countClockingActions()
		
	def _countClockingActions(self):
		allIns = [self.nReset, self.clock, *self.inputs]
		
		self.numClockingActions = allIns.count(BitValue.Clock)
		return self.numClockingActions
		
		
	def deepCopy(self):
		newV = TestStep('0', '0', '0')
		newV.nReset = self.nReset
		newV.clock = self.clock
		newV.inputs = [None] * len(self.inputs)
		for i in range(len(self.inputs)):
			newV.inputs[i] = self.inputs[i]
			
		if len(self.outputs):
			newV.outputs = [None] * len(self.outputs)
			for i in range(len(self.outputs)):
				newV.outputs[i] = self.outputs[i]
		
		newV.comment = self.comment
		newV._countClockingActions()
		return newV 
				
	def replaceAll(self, replaceBV:BitValue, withBV:BitValue):
		
		if self.nReset == replaceBV:
			self.nReset = withBV 
		if self.clock == replaceBV:
			self.clock = withBV 
			
		for i in range(len(self.inputs)):
			if self.inputs[i] == replaceBV:
				self.inputs[i] = withBV 
		for i in range(len(self.outputs)):
			if self.outputs[i] == replaceBV:
				self.outputs[i] = withBV 
		
		self._countClockingActions()
		return self 
	
	def copyWithReplace(self, replaceBV:BitValue, withBV:BitValue):
		newV = self.deepCopy()
		newV.replaceAll(replaceBV, withBV)
		return newV
		
	
	def ignoreOutputs(self):
		self.outputs = []
		
	def __str__(self):
		return f'{self.nReset} {self.clock} {self.inputs} {self.outputs} ({self.numClockingActions})'
			
		
		
	
class TruthMapping:
	def __init__(self, resultingValue:str, comment:str=''):
		self.result = SaneBinaryValue(resultingValue)
		self.comment = comment
		
		
	def __str__(self):
		return f'Expecting {self.result.binstr}'
		

class OneToOneTruthMapping(TruthMapping):
	def __init__(self, state:str, output:str, comment:str=''):
		super().__init__(output, comment)
		self.state = SaneBinaryValue(state)


	def __str__(self):
		if len(self.comment):
			return f'Set {self.ctrl.binstr} {self.state.binstr}, expect {self.result.binstr}\t#{self.comment}'
		
		return f'Set {self.ctrl.binstr} {self.state.binstr}, expect {self.result.binstr}'
		
		
class OneToOneTruthMappingWithControls(OneToOneTruthMapping):
	def __init__(self, ctrlBits:str, state:str, output:str, comment:str=''):
		super().__init__(state, output, comment)
		self.ctrl = SaneBinaryValue(ctrlBits)


		
		
class TruthTable:
	'''
		Holds the sequence/expected mapping of inputs -> outputs
		and provides an async testAll() to perform the testing.
	'''
	def __init__(self, interStepDelay:int=10, interStepTimeUnits:str='ns'):
		self.mappings = []
		self.stepDelayTime = interStepDelay
		self.stepDelayUnits = interStepTimeUnits
		
		
	def addMapping(self, relationship:TruthMapping):
		self.mappings.append(relationship)
		
	def getMapping(self, idx:int) -> TruthMapping:
		if idx >= len(self.mappings):
			raise IndexError('out of bounds on mapping')
			
		return self.mappings[idx]
		
	def numMappings(self):
		return len(self.mappings)
		
	def __len__(self):
		return self.numMappings()
		
	def __getitem__(self, idx:int):
		return self.getMapping(idx)
	
	def __str__(self):
		numsteps = len(self)
		retStrs = [f"Truthtable with {numsteps} mappings"]
		for i in range(numsteps):
			step = self[i]
			retStrs.append(f'{i + 1}\t{str(step)}')
			
		return '\n'.join(retStrs)
	
	def dump(self):
		print(str(self))
		
		
	async def testAll(self, clk, reset_n, i_bus, o_bus , logger=None):	
		for i in range(len(self)):
			reset_n.value = self[i].ctrl[1]
			clk.value = self[i].ctrl[0]
			i_bus.value = self[i].state
			await Timer(self.stepDelayTime, units=self.stepDelayUnits)  # wait a tad
			
			logger.debug(f'Set i_bus to {i_bus.value} vs {self[i].state}')
			for idx in range(8):
				logger.debug(f'{i}-{idx}: i_bus[{idx}] == {i_bus[idx]} == {self[i].state[idx]}')
				
			expectedResult = self[i].result
			if logger is not None:
				if len(self[i].comment):
					logger.info(self[i].comment)
				logger.info(f'State {i}, setting input to {self[i].ctrl} {self[i].state}, expecting {expectedResult} (got {o_bus.value})')
				
			# this is so stupid that it's probably wrong... there _must_ be
			# a good way to do this, otherwise _what_ is the point of having
			# unknown and don't care... but anyway, 
			# will die if o_bus[n] is some defined value
			# but we expect a don't know (x) or even a don't care (-), ugh
			# manual style
			for bit in range(len(o_bus)):
				if expectedResult.hardBit[bit]:
					# ok, safe to compare, duh
					# logger.info(f'Doing bit {bit}: {o_bus[bit]} == {expectedResult[bit]}')
					
					assert o_bus[bit] == expectedResult[bit]
		
		

class TestTableEntryParser:
	'''
		A little class that validates and cleans up 
		input and output specifications.
	'''
	
	def __init__(self, logger):
		self.log = logger
		self.optionalPrefix = r"(\d'|0b)?"
		self.validInputValues = r'(\s*[01tTcCxX-]\s*){8}' # 0/1 hard-coded, t/T toggle, c/C clocking, x or - unchanged
		self.validOutputValues = r'(\s*[01xX-]\s*){8}'  # 0/1 hard-coded,x or - don't care
		
		
		valueMatchReTpl = StringTemplate(r'\s*$prefix($valmatch)')
		self.inputValueValidatorRe = re.compile(
									  valueMatchReTpl.substitute(
										prefix=self.optionalPrefix, valmatch=self.validInputValues))
		self.outputValueValidatorRe = re.compile(
									  valueMatchReTpl.substitute(
										prefix=self.optionalPrefix, valmatch=self.validOutputValues))



	def validateAndClean(self, val:str, usingRegex):
		
		if val is None or not len(val):
			return None 
		
		
		mtch = usingRegex.match(val)
		
		
		if mtch is None:
			vcln = val.strip()
			if not len(vcln):
				# just whitespace
				return None 
			
			if vcln.find('#') >= 0 or vcln.find('//') >=0:
				# just a comment
				return None 
			
			if vcln.find('1') >=0 or vcln.find('0') >=0 or vcln.find('x') >= 0:
				self.log.error(f"Bad value passed ? '{val}'")
				
			return None 
		
		return re.sub(r'\s+', '', mtch.group(0)).lower()

	def inputFrom(self, val:str):
		return self.validateAndClean(val, self.inputValueValidatorRe)

	def outputFrom(self, val:str):
		if val is None or not len(val):
			return None
		return self.validateAndClean(val, self.outputValueValidatorRe)


class TestTableParser:
	'''
		Base class for tabular configuration values for input sequence and 
		expected outputs.
		
		This class handles maintaining the truth table and the state between
		steps in a sequence.
		
		Basically does everything except handle the particularities of a 
		give table format (e.g. markdown).
	
	'''
	
	def __init__(self, logger=None, numIOBits:int=8):
		if logger is None:
			logger = logging.getLogger(__name__)
		self.log = logger 
		self.numIOBits = numIOBits
		self.valueParser = TestTableEntryParser(self.log)
		
		
		self._truthTable = None 
		self._textTable = []
		
		self._ctrlBits = SaneBinaryValue('10')
		self._currentInput = SaneBinaryValue('0'*numIOBits)
		self._ignoreOutput = SaneBinaryValue('-'*numIOBits)
		
	
	def reset(self):
		self._currentInput = SaneBinaryValue('00000000')
		self._truthTable = None
		self._textTable = []
		
	@property 
	def truthTable(self) -> TruthTable:
		if self._truthTable is None:
			self._truthTable = TruthTable()
			
		return self._truthTable
	
	def _stateFromBits(self, inputBits:list, cache:dict):
		
		numBits = len(inputBits)
		newBits = ['0'] * numBits
		
		for i in range(numBits):
			bv = inputBits[i]
			if BitValue.isDigitalValue(bv):
				cache[i] = bv.value
				newBits[i] = str(bv.value)
			elif bv == BitValue.Toggle:
				cache[i] = ~cache[i]
				newBits[i] = str(cache[i])
			else:
				# unchanged 
				newBits[i] = str(cache[i])
				
		
		return newBits
				
	
	
	def _ctrlStateFromBits(self, nReset:BitValue, clock:BitValue):
		return self._stateFromBits([nReset, clock], self._ctrlBits)
			
	def _inputStateFromBits(self, inputBits):
		return self._stateFromBits(inputBits, self._currentInput)
				
	
	def _inputStateFromBits2(self, inputBits):
		
		newBits = ['0'] * self.numIOBits
		
		for i in range(self.numIOBits):
			
			if inputBits[i] == '0' or inputBits[i] == '1':
				newBits[i] = inputBits[i]
				self._currentInput[i] = int(inputBits[i])
			elif inputBits[i] == 't':
				# toggled
				self._currentInput[i] = ~self._currentInput[i]
				newBits[i] = str(self._currentInput[i])
			else:
				# unchanged
				newBits[i] = str(self._currentInput[i])
				
		
		return ''.join(newBits)
	
	
	def addTruthTableMapping(self, step:TestStep):
		if step.numClockingActions:
			raise ValueError(f'Cannot add step with clocking actions: {str(step)}')
		
		ctrlBinVal = SaneBinaryValue(self._ctrlStateFromBits(step.nReset, step.clock))
		
		inputBinVal = SaneBinaryValue(self._inputStateFromBits(step.inputs))
		
		outputBinVal = self._ignoreOutput
		
		if len(step.outputs):
			# self.log.info(f'outval is "{step.outputs}"')
			outputBinVal = SaneBinaryValue(step.outputs)
		 
		self.truthTable.addMapping(OneToOneTruthMappingWithControls(ctrlBinVal.binstr, inputBinVal.binstr, outputBinVal.binstr, step.comment))
		self._textTable.append(step)
		return True
				
	def addStep(self, step:TestStep):
		# step = TestStep(nReset, clock, inputs, outputs)
		
		if not step.numClockingActions:
			self.addTruthTableMapping(step)
			return 
		
		# have clocking... need to append multiple 
		# events to mapping 
		
		# do setup
		# replace clocking by 'no action'
		setupStep = step.copyWithReplace(BitValue.Clock, BitValue.NoAction)
		setupStep.ignoreOutputs()
		setupStep.comment = ''
		
		# next: leave clocking on, but replace any toggles with no action
		# so we don't double toggle,
		# copy from original
		clockStep1 = step.copyWithReplace(BitValue.Toggle, BitValue.NoAction)
		
		clockStep1.replaceAll(BitValue.Clock, BitValue.Toggle)
		# get a second clocking step, no toggle
		clockStep2 = clockStep1.deepCopy()
		
		# and ignore the outputs on that first clock substep
		clockStep1.ignoreOutputs()
		clockStep1.comment = ''
		
		# now add these steps as well, so each clocking step 
		# becomes a sequence of 3 in mapping
		
		self.addTruthTableMapping(setupStep) # this steps sets bits and toggles toggled
		
		self.addTruthTableMapping(clockStep1) # this clocks the clocks, leaves toggles alone, ignores outputs
		self.addTruthTableMapping(clockStep2) # same as previous, but preserves outputs oof
	
		
	def addStep2(self, nReset:str, clock:str, inputValue:str, outputValue:str=''):
		inputBits = self.valueParser.inputFrom(inputValue)
		
		if inputBits is None or not len(inputBits):
			self.log.info(f'Unable to parse input bits: {inputValue}')
			return False 
		
		if inputBits.find('c') >= 0:
			# clocking...
			setupInputs = inputBits.replace('c', 'x')
			self.log.debug(f'Have clocking in inputs {inputBits}, adding setup step {setupInputs}')
			self.addStep(setupInputs) # setup
			
			# clock edge 1
			
			clockEdges = inputBits.replace('t', 'x') # don't toggle twice!
			
			clockInAndHold = clockEdges.replace('c', 't')
			
			self.log.debug(f'Now clock {clockEdges} x2')
			
			self.addStep(clockInAndHold) # clock in
			
			# clock edge 2
			self.addStep(clockInAndHold) # clock out
		
		
		inputBinVal = SaneBinaryValue(self._inputStateFromBits(inputBits))
		
		outputBinVal = self._ignoreOutput
		
		outputBits = ''
		if outputValue is not None and len(outputValue):
			self.log.info(f'outval is "{outputValue}"')
			outputBits = self.valueParser.outputFrom(outputValue)
			if outputBits is None or not len(outputBits):
				self.log.info(f'Unable to parse output bits: {outputBits}')
				return False 
			
			outputBinVal = SaneBinaryValue(outputBits)
			
			
			
			
		self.log.info(f'Mapped {inputBits} -> {outputBits} ({inputBinVal} -> {outputBinVal})')
		
		self.truthTable.addMapping(OneToOneTruthMapping(inputBinVal.binstr, outputBinVal.binstr))
		self._textTable.append((inputBits, outputBits))
		return True
	
	def generateFrom(self, contents:str):
		self.reset() # reset the table
		self.log.error("Override generateFrom() in subclass")
		return None 
	
	
	def __str__(self):
		retStrs = [f'Truth table parser with {len(self._textTable)} steps added.']
		for i in range(len(self._textTable)):
			step = self._textTable[i]
			if step.outputs is not None and len(step.outputs):
				retStrs.append(f'{i+1}\t{step.nReset}, {step.clock}, {step.inputs} -> {step.outputs} {step.comment}')
			else:
				retStrs.append(f'{i+1}\t{step.nReset}, {step.clock}, {step.inputs} {step.comment}')
		
		return '\n'.join(retStrs)
	
	def dump(self):
		print(str(self))
				
			
	
	
class MarkdownTestTableParser(TestTableParser):
	'''
		A specialization of the TestTableParser that handles the 
		particulars of extracting test inputs/outputs from a markdown 
		table.
	'''
	
	def __init__(self, columnSeparatorRegex:str=r'\|', logger=None):
		'''
		We want to support markdown tables.
		These may have some header row, followed by a separator (which may
		or may not include aligment info, i.e. ':'), finally followed 
		by our content of interest.  E.g.
		
			| some name | another  | <- column headers
			|-----------|---------:| <- header sep 
			| CONTENT   | CONTENT  | <- actual content of interest
			
			CONTENT is 8 bits, MSB
			 [7    ...     0]
			 A B C D E F G H
			 
			Where each bit is either:
			   0
			   1
			   X (or x) don't change/don't care
			   T (or t) toggle
			   C (or c) clock
			...
			
		
		'''
		super().__init__(logger)
		self.bitSettingsRe = re.compile(r'^([01xXtTcC\s-])+$')
		self.columnSeperatorRe = columnSeparatorRegex
		eol = r'(\r\n|\r|\n)' 
		
		
		
		# the |-------|----- ... line
		tableHeaderSepTpl = StringTemplate(r'\s*($sep\s*:?-{1,}:?\s*){2,}$sep$eol')
		self.headerSepRe = re.compile(tableHeaderSepTpl.substitute(sep=self.columnSeperatorRe, eol=eol), re.M)

		# each content line thereafter
		# | CONTENT | CONTENT |
		contentRowTpl = StringTemplate(r'^\s*(($sep\s*[^$sep\r\n]+){1,})$sep$eol')
		self.contentRowRe = re.compile(contentRowTpl.substitute(sep=self.columnSeperatorRe, eol=eol), re.M)
		
		
		self.rowItemSplitterRe = re.compile(self.columnSeperatorRe)
		
	def parseMarkdownTable(self, contents:str):
		contentRowMatches = self.contentRowRe.findall(contents)
		ttableRows = []
		pastHeader = False
		for aMatch in contentRowMatches:
			fullLine = aMatch[0]
			cols = re.split(self.columnSeperatorRe, fullLine)
			if not pastHeader:
				if len(cols) < 2:
					continue 
				if len(cols[1]) and (len(cols[1].replace('-', '')) == 0):
					pastHeader = True 
				
				continue
			
			# we have made it past header
			row = []
			numComments = 0
			numBitfields = 0
			for acolumn in cols[1:]:
				bitMatch = self.bitSettingsRe.match(acolumn)
				if bitMatch is not None and len(bitMatch.group(0)):
					row.append(re.sub(r'\s+', '', bitMatch.group(0)))
					numBitfields += 1
				else:
					row.append(acolumn.strip())
					if numComments:
						raise ValueError(f'Have multiple non-bit columns in table? "{acolumn}"')
					numComments += 1
			
			if numBitfields < 3:
				raise ValueError(f'Not enough bitfields in table row\n{fullLine}')
			
			ttableRows.append(row)
			
		# we now have all the active rows in a single array of arrays
		# RC,  INPUTS, OUTPUT, [comment]
		for aRow in ttableRows:
			comment = ''
			if len(aRow) > 3:
				comment = aRow[3]
			# print(f"COMMENT IS {comment}")
			self.addStep(TestStep(aRow[0][0], aRow[0][1], aRow[1], aRow[2], comment))
			
		return len(ttableRows)
				
				
				
			
			
		
	def parseMarkdownTable2(self, contents:str):
		
		headerSepSearch = self.headerSepRe.search(contents)
		if headerSepSearch is not None:
			# did have a header
			# dump it, and everything before it
			headerSpan = headerSepSearch.span()
			headerEndPos = headerSpan[1] 
			self.log.debug(f"Dumping header to {headerEndPos}\n{contents[:headerEndPos]}")
			contents = contents[headerEndPos:]
			
		# extract valid rows in first pass 
		self.log.debug(f"Content row RE is {self.contentRowRe}")
		contentRowMatches = self.contentRowRe.findall(contents)
		if contentRowMatches is None or not len(contentRowMatches):
			self.log.error('No valid rows found in markdown table')
			return False
		
		
		numSteps = 0
		for aRow in contentRowMatches:
			self.log.debug(f'Matched row {aRow}')
			entries = self.rowItemSplitterRe.split(aRow[0])
			
			# note, we have entries like
			# SEP AAA SEP BBB SEP
			# so splitting on SEP gives us an empty entry at front of list
			# hence the requirement for len == 2 for at least 1 entry, len == 3 
			# for input and output.
			
			if len(entries) < 2:
				self.log.info(f'Row has insufficient entries ? ("{aRow[0]}")')
				continue
			
			inVal = entries[1]
			outVal = None 
			
			if len(entries) > 2 and len(entries[2]):
				outVal = entries[2].strip()
				
			if self.addStep(inVal, outVal):
				numSteps += 1
				
		
		return numSteps
				
			
			

	def generateFrom(self, contents:str):
		
		self.reset()
		
		tableParsed = self.parseMarkdownTable(contents)
		
		if tableParsed is None or not tableParsed:
			self.log.error("Could not extract truthtable from contents")
			return None 
		
		return self.truthTable
		
		
		



def parseSimpleTable(contents:str):
	tt = TruthTable()
	m = re.compile(r'''^\s*\d'(\d+)\s*\|\s*\d'([zZxX\d]+)''', re.M)
	for match in m.findall(contents):
		if match[1] != 'x':
			# we skip anything where all results are don't care
			# result = match[1].replace('x', '-') # now using the BinaryValue override
			result = match[1]
			tt.addMapping(OneToOneTruthMapping(match[0],result))
		
	return tt

def parseMarkdownTable(contents:str, logger=None):
	m = MarkdownTestTableParser(logger=logger)
	table = m.generateFrom(contents)
	return table
	
	
def loadSimpleTruthTable(filepath:str):
	with open(filepath, 'r') as f:
		contents = f.read()
		return parseSimpleTable(contents)
	
	return None


def loadMarkdownTruthTable(filepath:str, logger=None): 
	with open(filepath, 'r') as f:
		contents = f.read()
		return parseMarkdownTable(contents, logger)
	
	return None

TruthTableExample = '''
     \\ui_in | \\uo_out
 ---------- | -----------
 8'11111000 | 8'xxxxxxx0
 8'11111001 | 8'xxxxxxx1
 8'11111010 | 8'xxxxxxx0
 8'11111011 | 8'xxxxxxx1
 8'11111100 | 8'xxxxxxx0
 8'11111101 | 8'xxxxxxx1
 8'11111110 | 8'xxxxxxx1
 8'11111111 | 8'xxxxxxx0

'''

# with comments and spacing
TruthTableMarkdownExample  = '''
This is some random comments text...

and more 

|RC| D  C  B  A  CDIS xxx |    segments     |        comment         |
|--|----------------------|-----------------|------------------------|
|10| 0  0  0  0    1  000 |   -111 1000     |    disable clocking    |
|xx| 0  0  0  1    x  xxx |   -111 1011     |    0b0001 (AB'C'D')    |
|xx| 0  0  1  0    x  xxx |   -000 0000     |    0b0010 (A'BC'D')    |
|xx| 0  1  0  0    x  xxx |   -101 0100     |    0b0100 (A'B'CD')    |
|xx| 1  0  0  0    x  xxx |   -001 0000     |    0b1000 (A'B'C'D)    |
|xx| 1  0  0  1    x  xxx |   -101 1100     |    AB'C'D: "o"         |
|1c| 0  0  0  0    0  xxx |   ---- ----     |  enable clocking+reset |
|0c| x  x  x  x    x  xxx |   -111 1000     |    T                   |
|xc| x  x  x  x    x  xxx |   -001 0000     |    i                   |
|xc| x  x  x  x    x  xxx |   -101 0100     |    n                   |
|xc| x  x  x  x    x  xxx |   -110 1110     |    y                   |
|xc| x  x  x  x    x  xxx |   -000 0000     |    "space"             |
|xc| x  x  x  x    x  xxx |   -111 1000     |    t                   |
|xc| x  x  x  x    x  xxx |   -111 0111     |    a                   |
|xc| x  x  x  x    x  xxx |   -111 0011     |    p                   |
|xc| x  x  x  x    x  xxx |   -111 1011     |    e                   |
|xc| x  x  x  x    x  xxx |   -101 1100     |    o                   |
|xc| x  x  x  x    x  xxx |   -001 1100     |    u                   |
|xc| x  x  x  x    x  xxx |   -111 1000     |    t                   |
|xc| x  x  x  x    x  xxx |   -111 1000     |    T                   |

booya
'''
if __name__ == "__main__":
	m = MarkdownTestTableParser()
	table = m.generateFrom(TruthTableMarkdownExample)
	
	m.dump()
	table.dump()
	#tt = parseSimpleTable(TruthTableExample)
	#print(f'with state {tt[0].state} you get {tt[0].result}')
