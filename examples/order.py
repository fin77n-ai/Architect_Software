from calc import calculate_discount

def process_order():
    total = 100
    # 错误发生在这里：传了一个字符串 "0.2" 给底层函数
    discount = "0.2"
    final_total = calculate_discount(total, discount)
    print(f"最终价格: {final_total}")

process_order()
