from GoParser import GoParser
from GoParserListener import *
from enum import Enum
from graphviz import * 
from re import *
from copy import copy, deepcopy 

class State(Enum):
	none = 0
	const_decl = 1
	var_decl = 2
	assign = 3
	in_if = 4
	in_for = 5
	in_return = 6

class Fork:
	IfThen = 1
	IfThenElse = 2
	For = 3

	def __init__(self, t, level):
		self.level = level
		self.type = t

class NodeType(Enum):
	FuncBegin = -3
	FuncEnd = -2
	Decl = -1
	Assign = 0
	IfThen = 1
	IfThenElse = 1
	Then = 2
	Else = 3
	For = 4
	Function = 5

def extract_values(ctx):
	children = [ctx.getChild(i).getText() for i in range(0, ctx.getChildCount(), 2)]
	return children

def style(node, dir):
	if ':' in node:
		return node
	return f'{node}:{dir}'

class Node:
	def __init__(self, name: str, cont:str, type: NodeType):
		self.type:NodeType = type
		self.cont = cont
		self.children: list['Node'] = []
		self.name = name
		
	def lasts(self):
		stack = [self]
		visited = set()
		ret = []
		while stack:
			last = stack.pop()

			if not last.children or \
					len(last.children)==1 and last.type == NodeType.For or \
					len(last.children)==1 and last.type in [NodeType.IfThenElse]:
					ret.append(last)

			if last.full_name() in visited:
				continue
			visited.add(last.full_name())
			stack.extend(last.children)
		
		if not ret:
			return [self]
		
		return ret
	
	def add_child(self, node):
		if node not in self.children:
			self.children.append(node)
	
	def connect_to_bottom(self, node):
		lasts = self.lasts()
		for last in lasts:
			last.add_child(node)

	def full_name(self):
		return f'{self.type}+{self.name}'

	def __repr__(self) -> str:
		return f'Node({self.cont}, {self.children})'
	
class CFGRenderer:
	def __init__(self, cfg):
		self.cfg = cfg
		self.lasts = []
		self.graph = Digraph('cfg', format='png')
		self.graph.attr(rankdir='TB')
		self.ready_nodes = set()

	def render(self):
		for node in self.cfg.node_stack:
			self.render_node(node)

		self.graph.render()

	def render_node(self, node:Node):
		name = node.full_name()

		if name not in self.ready_nodes:
			self.ready_nodes.add(name)

			for ch in node.children:
				self.render_node(ch)

			if node.type in [NodeType.IfThen, NodeType.IfThenElse]:
				self.render_if(node)

			if node.type == NodeType.For:
				self.render_for(node)

			if node.type in [NodeType.Assign, NodeType.Decl, NodeType.FuncEnd, NodeType.FuncBegin]:
				self.render_basic_node(node)

	def render_basic_node(self, node:Node):
		name = node.full_name()
		if node.type in [NodeType.FuncEnd, NodeType.FuncBegin]:
			self.graph.node(name, node.cont, shape='trapezium')
		else:
			self.graph.node(name, node.cont, shape='box')

		for ch in node.children:
			child = ch
			self.graph.edge(name, child.full_name(), headport='n', tailport='s')

	def render_if(self, node:Node):
		name = node.full_name()
		self.graph.node(name, node.cont, shape='diamond')

		self.graph.edge(name, node.children[0].full_name(), headport='n', tailport='w', color='green')
		self.graph.edge(name, node.children[1].full_name(), headport='n', tailport='e', color='red')

	def render_for(self, node:Node):
		name = node.full_name()

		self.graph.node(name, node.cont, shape='egg')

		self.graph.edge(name, node.children[0].full_name(), headport='nw', tailport='w', color='green', constraint='false')
		self.graph.edge(name, node.children[1].full_name(), headport='n', tailport='s', color='red')

class CFGListener(GoParserListener):
	def __init__(self, *args, **kwargs):
		self.state = State.none
		self.typed_const = False
		self.names_set = False
		self.values_set = False
		
		self.level = 0
		
		self.stack = []

		self.ind = 0

		self.cur_text = ''
		self.node_stack: list[Node] = []
		self.block:list[list[Node]] = []

		self.ready_nodes = []

		self.forks = []

	def fresh_ind(self):
		self.ind+=1
		return str(self.ind)

	def assign(self, keyword='', op='='):
		vals = self.stack.pop()
		t = self.stack.pop()
		names = self.stack.pop()
	
		# TODO compare len(vals) and len(names)

		for i in range(len(vals)):
			text = ''
			if keyword:
				if t == 'guess':
					text = f'{keyword} {names[i]} = {vals[i]} \n'

				else:
					text = f'{keyword} {names[i]} {t} = {vals[i]} \n'
				
				self.block[-1].append(Node(self.fresh_ind(), text, NodeType.Decl))
			else:
				text = f'{names[i]} {op} {vals[i]} \n'
				self.block[-1].append(Node(self.fresh_ind(), text, NodeType.Assign))

		self.names_set = False
		self.values_set = False
		self.state = State.none

	def enterFunctionDecl(self, ctx):
		self.block.append([Node(self.fresh_ind(), 'begin '+ctx.getChild(1).getText(), NodeType.FuncBegin)])

	def exitFunctionDecl(self, ctx):
		end = Node(self.fresh_ind(), 'end '+ctx.getChild(1).getText(), NodeType.FuncEnd)
		self.finish_block()
		func = self.block.pop()[0]

		func.connect_to_bottom(end)
		
		self.node_stack.append(func)

	def enterBlock(self, ctx):
		self.level += 1
		self.block.append([])
		
	def exitBlock(self, ctx):
		self.level -= 1
		self.finish_block()

	def enterConstSpec(self, ctx):
		self.state = State.const_decl

	def exitConstSpec(self, ctx):
		self.assign('const')
		self.typed_const = False

	def enterVarDecl(self, ctx):
		self.state = State.var_decl

	def enterAssignment(self, ctx):
		self.state = State.assign
		names = extract_values(ctx.getChild(0))
		op = ctx.getChild(1).getText()
		t = 'guess'
		values = extract_values(ctx.getChild(2))

		self.stack.append(names)
		self.stack.append(t)
		self.stack.append(values)

		self.assign(op=op)

	def exitPrimaryExpr(self, ctx):
		if self.state == State.none:
			if ctx.getChildCount() == 2:
				self.block[-1].append(Node(self.fresh_ind(), ctx.getText(), NodeType.Decl))

	def enterReturnStmt(self, ctx):
		self.state = State.in_return

	def exitReturnStmt(self, ctx):
		self.block[-1].append(Node(self.fresh_ind(), 'return '+ctx.getChild(1).getText(), NodeType.Decl))
		self.state = State.none

	def exitVarDecl(self, ctx):
		self.assign('var')
		self.typed_const = False	
		self.state = State.none

	def exitIdentifierList(self, ctx):
		if self.state in [State.const_decl, State.var_decl, State.assign]:
			if self.names_set:
				return
			
			self.names_set = True

			self.stack.append(extract_values(ctx))

	def exitType_(self, ctx):
		if self.state in [State.const_decl, State.var_decl, State.assign]:
			self.stack.append(ctx.getChild(0).getChild(0).getText())
			self.typed_const = True

	def finish_block(self):
		if self.block[-1]:
			block = self.block.pop()
			node = block[0]

			for n in block[1:]:
				node.connect_to_bottom(n)

			level_ok = self.forks and self.forks[-1].level == self.level
			
			if_order_ok = self.forks and self.forks[-1].type in [Fork.IfThen, Fork.IfThenElse]
			for_order_ok = self.forks and self.forks[-1].type == Fork.For

			prev_if = \
				self.block and \
				self.block[-1] and \
				self.block[-1][-1].type == NodeType.IfThen
			
			prev_then = \
				len(self.block)>1 and \
				self.block[-2] and \
				self.block[-2][-1].type == NodeType.IfThenElse and \
				self.forks and self.forks[-1].type == Fork.IfThenElse
			
			prev_for = \
				self.block and \
				self.block[-1] and \
				self.block[-1][-1].type == NodeType.For

			if_ok = if_order_ok and (prev_if or prev_then)
			for_ok = for_order_ok and prev_for

			if self.block and (not self.forks or level_ok and not (if_ok or for_ok)):
				self.block[-1].append(node)
			else:
				self.block.append([node])

			pass

	def exitExpressionList(self, ctx):
		if self.state in [State.const_decl, State.var_decl]:
			if self.values_set:
				self.stack.pop()

			self.values_set = True
			if not self.typed_const:
				self.stack.append('guess')
			self.stack.append(extract_values(ctx))

	def enterIfStmt(self, ctx):
		self.state = State.in_if
		self.finish_block()
		if ctx.getChildCount() == 3: 
			self.forks.append(Fork(Fork.IfThen, self.level))
			self.block[-1].append(Node(self.fresh_ind(), ctx.getChild(1).getText(), NodeType.IfThen))

		if ctx.getChildCount() == 5:
			self.forks.append(Fork(Fork.IfThenElse, self.level))
			self.block[-1].append(Node(self.fresh_ind(), ctx.getChild(1).getText(), NodeType.IfThenElse))

	def exitIfStmt(self, ctx):
		if ctx.getChildCount() == 5:
			elsenode = self.block.pop()[0]
			thennode = self.block.pop()[0]

			ifnode = self.block[-1].pop()

			ifnode.add_child(thennode)
			ifnode.add_child(elsenode)

			self.block[-1].append(ifnode)
		else:
			thennode = self.block.pop()[0]
			ifnode = self.block[-1].pop()

			ifnode.add_child(thennode)

			self.block[-1].append(ifnode)

		self.forks.pop()
		self.state = State.none


	def enterForStmt(self, ctx):
		self.state = State.in_for
		self.finish_block()
		self.forks.append(Fork(Fork.For, self.level))
		
		self.block[-1].append(Node(self.fresh_ind(), ctx.getChild(1).getText(), NodeType.For))
		

	def exitForStmt(self, ctx):
		blocknode = self.block.pop()[0]
		fornode = self.block[-1].pop()

		blocknode.connect_to_bottom(fornode)
		fornode.add_child(blocknode)

		self.block[-1].append(fornode)

		self.forks.pop()
		self.state = State.none
		