exponent_amount = "1.1e6"
amount_list_exp = []

# splitting the exponential value into its component parts
for item in exponent_amount:
    amount_list_exp.append(item.lower())


# declaring a function to find out whether input contains exponents or not
def is_exponential(array: list):
    if "e" in array:
        return True
    return False


# using the above function, iterates through each item
if is_exponential(amount_list_exp):
    before_e = []
    after_e = []
    for item in amount_list_exp:
        if item != "e":
            before_e.append(item)  # appends the numbers before exponent value in a separate before_e list
        else:
            exponent_pos = amount_list_exp.index("e")  # finds the index position of the exponent itself
            after_e.append(amount_list_exp[exponent_pos+1:])  # appends everything after the exponent to another separate after_e list
            break

    before_e_str, ten_exponent = "".join(before_e), "".join(
        after_e[0])  # concatenate the iterables to their respective strings

    exponent_value = 10 ** int(ten_exponent)
    actual_value = eval(f'{before_e_str}*{exponent_value}')
else:
    actual_value = exponent_amount

# amount = int(actual_value)
print(before_e_str, exponent_value)
print(int(actual_value))


#    norm_amount = "1000000"
#    amount_list_norm = []
#
#    for integer in norm_amount:
#       amount_list_norm.append(integer)
