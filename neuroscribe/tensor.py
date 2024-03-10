from functools import partial

import numpy as np


class Function:
    def __call__(self, *args):
        self.args = args
        return self.forward(*args)

    def forward(self, *args): raise NotImplementedError(f"forward not implemented for {type(self)}")
    def backward(self, grad_output): raise RuntimeError(f"backward not implemented for {type(self)}")


import neuroscribe.mlops as mlops


class Tensor:

    def __init__(self, data, dtype='float64', requires_grad=False, device='cpu'):
        self.data = np.array(data, dtype=dtype)
        self.dtype = self.data.dtype
        self.size = self.data.size
        self.shape = self.data.shape
        self.strides = self.data.strides
        self.device = device  # TODO: Add support to devices other than CPU
        self.requires_grad = requires_grad
        self.grad = np.zeros(self.shape, dtype=self.dtype)
        self.grad_fn = lambda: None
        self._prev = list()

    @staticmethod
    def zeros(shape, dtype='float64'):
        return Tensor(np.zeros(shape, dtype=dtype), dtype=dtype)

    @staticmethod
    def ones(shape, dtype='float64'):
        return Tensor(np.ones(shape, dtype=dtype), dtype=dtype)

    def backward(self):
        graph = []
        visited = set()

        def build_graph(tensor):
            if tensor not in visited:
                visited.add(tensor)
                for child in tensor._prev:
                    build_graph(child)
                graph.append(tensor)
        build_graph(self)

        self.grad = np.ones(self.shape, dtype=self.dtype)
        for tensor in reversed(graph):
            tensor.grad_fn()

    def __repr__(self):
        return f"Tensor({self.data}, dtype={self.dtype})"

    def is_contiguous(self):
        return self.data.flags['C_CONTIGUOUS']

    def make_contiguous(self):
        self.data = np.ascontiguousarray(self.data)

    def deep_copy(self):
        return Tensor(self.data.copy(), dtype=self.dtype, requires_grad=self.requires_grad)

    def shallow_copy(self):
        return Tensor(self.data, dtype=self.dtype, requires_grad=self.requires_grad)

    def to(self, dtype):
        if dtype == self.dtype:
            return self
        else:
            return Tensor(self.data, dtype=dtype, requires_grad=self.requires_grad)

    # Shape manipulation methods
    def reshape(self, new_shape):
        return Tensor(self.data.reshape(new_shape), dtype=self.dtype, requires_grad=self.requires_grad)

    def transpose(self, axes=None):
        return Tensor(self.data.transpose(axes), dtype=self.dtype, requires_grad=self.requires_grad)

    def split(self, indices_or_sections, axis=0):
        result = np.split(self.data, indices_or_sections, axis)
        return [Tensor(x, dtype=self.dtype, requires_grad=self.requires_grad) for x in result]

    def _exec_op(self, t1, t2, _op):
        if not isinstance(t2, Tensor):
            t2 = Tensor(t2, dtype=t1.dtype)

        result_tensor = Tensor(_op(t1, t2), dtype=t1.dtype,
                               requires_grad=t1.requires_grad or t2.requires_grad)

        if result_tensor.requires_grad:
            result_tensor.grad_fn = partial(_op.backward, result_tensor)
            result_tensor._prev.append(t1)
            result_tensor._prev.append(t2)

        return result_tensor

    # Tensor Operations
    # TODO: Add more ops
    def __add__(self, other): return self._exec_op(self, other, mlops.Add())
    def __mul__(self, other): return self._exec_op(self, other, mlops.Mul())