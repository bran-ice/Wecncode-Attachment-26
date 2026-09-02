def promo_discount(subtotal, promo_code):
    if promo_code == 'SUMMER':
        return subtotal * 0.15
    elif promo_code == 'WELCOME5':
        return 5.0
    else:
        return 0.0

def bulk_discount(subtotal, is_catering):
    if is_catering and subtotal > 200:
        return 25.0
    else:
        return 0.0

def loyalty_credit(loyalty_points):
    if loyalty_points > 100:
        return 5.0
    else:
        return 0.0

def tax_rate_for_city(city):
    if city == 'Local':
        return 0.08
    else:
        return 0.10

def final_total(subtotal, promo_code=None, city='Local', is_catering=False, loyalty_points=0):
    p = promo_discount(subtotal, promo_code)
    b = bulk_discount(subtotal, is_catering)
    l = loyalty_credit(loyalty_points)
    total_discount = p + b + l
    rate = tax_rate_for_city(city)
    taxed = (subtotal - total_discount) * (1 + rate)

    print("Subtotal:", subtotal)
    print("Promo discount:", p)
    print("Bulk discount:", b)
    print("Loyalty credit:", l)
    print("Tax rate:", rate)
    final = round(taxed, 2)
    print("Final total:", final)
    return final