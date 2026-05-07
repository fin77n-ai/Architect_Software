def calculate_discount(price, discount_rate):
    # 假设这里有一些复杂的逻辑
    final_price = price - (price * discount_rate)
    return final_price

def process_order(user_cart):
    total = 100
    # 哎呀，不小心把折扣率传成了一个字符串！
    discount = "0.2" 
    final_total = calculate_discount(total, discount)
    print(f"订单总价: {final_total}")

process_order({"item": "apple"})
