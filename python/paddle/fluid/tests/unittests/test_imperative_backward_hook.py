#   Copyright (c) 2019 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import unittest
import paddle.fluid as fluid
import paddle.fluid.core as core
from paddle.fluid.dygraph import nn
from paddle.fluid.optimizer import SGDOptimizer
from paddle.fluid.dygraph.base import to_variable
import numpy as np


class SimpleNet(fluid.Layer):
    def __init__(self, input_size, linear1_size=4):
        super(SimpleNet, self).__init__()
        self.linear1 = nn.Linear(input_size, linear1_size, bias_attr=False)
        self.linear2 = nn.Linear(linear1_size, 1, bias_attr=False)

    def forward(self,
                x,
                register_hook1=False,
                remove_hook1=False,
                register_hook2=False,
                remove_hook2=False,
                hook1=None,
                hook2=None):
        ret = self.linear1(x)
        if register_hook1:
            removable_hook1 = ret.register_hook(hook1)
        if register_hook2:
            removable_hook2 = ret.register_hook(hook2)
        if remove_hook1:
            removable_hook1.remove()
        if remove_hook2:
            removable_hook2.remove()
        ret = self.linear2(ret)
        return ret


def hook_fn1(grad1):
    print(2 * grad1)


def hook_fn2(grad2):
    print(4 * grad2)


def hook_fn3(grad3):
    grad3 = grad3 * 2
    return grad3


def hook_fn4(grad4):
    grad4 = grad4 * 4
    return grad4


class TestBackwardHook(unittest.TestCase):
    def register_remove_hook(self, register_hook1, remove_hook1, register_hook2,
                             remove_hook2, hook1, hook2):
        seed = 100
        fluid.default_startup_program().random_seed = seed
        fluid.default_main_program().random_seed = seed

        simple_net = SimpleNet(input_size=3)
        sgd = SGDOptimizer(
            learning_rate=1e-3, parameter_list=simple_net.parameters())

        x_data = np.arange(9).reshape(3, 3).astype('float32')
        x = to_variable(x_data)
        outs = simple_net(x, register_hook1, remove_hook1, register_hook2,
                          remove_hook2, hook1, hook2)
        dy_loss = outs
        dy_loss.backward()
        print(simple_net.linear1.weight._grad_ivar())
        sgd.minimize(dy_loss)
        sgd.clear_gradients()

    def test_backeard_hook_for_varbase(self):
        places = [fluid.CPUPlace()]
        if core.is_compiled_with_cuda():
            places.append(fluid.CUDAPlace(0))

        for place in places:
            with fluid.dygraph.guard(place):
                self.register_remove_hook(True, True, True, True, hook_fn1,
                                          hook_fn2)
                self.register_remove_hook(True, True, True, False, hook_fn1,
                                          hook_fn2)
                self.register_remove_hook(True, False, True, False, hook_fn1,
                                          hook_fn3)
                self.register_remove_hook(True, True, True, False, hook_fn1,
                                          hook_fn4)
                self.register_remove_hook(True, False, True, False, hook_fn4,
                                          hook_fn1)


if __name__ == '__main__':
    unittest.main()
