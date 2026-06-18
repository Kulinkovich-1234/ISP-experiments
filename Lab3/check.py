#!/usr/bin/env python3
"""
从 output.txt 读取一行内的多个整数（空格/逗号分隔），
随机抽取 10% 进行 Miller–Rabin 素性检验，
输出通过检验的数量。
"""

import re
import random
import sys

# ---------- Miller–Rabin 确定性检验（n < 2^32）----------
def is_prime(n: int) -> bool:
    if n < 2:
        return False
    # 小素数快速排除
    small_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    if n in small_primes:
        return True
    for p in small_primes:
        if n % p == 0:
            return False

    # 将 n-1 分解为 d * 2^s
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1

    # 基组 [2, 7, 61] 对 32 位整数是确定性的
    for a in (2, 7, 61):
        if a % n == 0:
            continue
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1:
                break
        else:
            return False
    return True

# ---------- 解析单行或多行，支持空格/逗号分隔 ----------
def extract_numbers(filename: str) -> list:
    """从文件中读取所有整数（支持一行内多数字）。"""
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    # 使用正则提取所有整数（负号可选，但质数不会为负）
    numbers = list(map(int, re.findall(r'-?\d+', content)))
    return numbers

def main():
    input_file = "output.txt"
    sample_ratio = 1
    random.seed(42)   # 固定种子便于复现，可删除

    # 1. 读取所有质数
    primes = extract_numbers(input_file)
    if not primes:
        print("错误：文件中未找到任何整数。", file=sys.stderr)
        sys.exit(1)

    total = len(primes)
    print(f"从 {input_file} 解析到 {total} 个整数（应为质数）。")

    # 2. 抽取 10% 样本
    sample_size = max(1, int(total * sample_ratio))
    if sample_size > total:
        sample_size = total
    sample = random.sample(primes, sample_size)
    print(f"抽取 {sample_size} 个样本（约 {sample_ratio*100:.0f}%）。")

    # 3. 检验样本
    passed = 0
    for idx, num in enumerate(sample, start=1):
        if is_prime(num):
            passed += 1
        else:
            # 若发现合数，输出其值（用于排查文件是否包含误判）
            print(f"警告：样本 #{idx} 值为 {num} —— 不是质数！", file=sys.stderr)

    # 4. 输出结果（只输出通过检验的数量）
    print(f"\n通过检验数量: {passed} / {sample_size}")

if __name__ == "__main__":
    main()