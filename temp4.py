import os
import numpy as np


pause = 0
sig = 0  # 用于清除lil_washer中的计时器，1时清除washing_time, 2时清除soaping_time，3清除drying_time
print('a: ', id(pause), '=', pause)
print('b: ', id(sig), '=', sig)
print(type(sig))
CLEAR_SIG = 1
print('b: ', id(CLEAR_SIG), '=', CLEAR_SIG)