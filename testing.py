
class Profile:

    users = 0
    pay_rate_increase = 1.2
    """Class used to define user's profile and their associated properties."""
    def __init__(self, first, last, age, gender, pay):
        self.first = first
        self.last = last
        self.age = age
        self.gender = gender
        self.pay = pay

        Profile.users += 1

    def __repr__(self):
        return f"Profile(first={self.first}, last={self.last}, age={self.age})"

    def __str__(self):
        return f"{self.first} {self.last} is {self.age} years old and has a pay of {self.pay}"

    def __add__(self, other):
        return self.pay + other.pay

    def __len__(self):
        return len(self.get_full_name())

    def get_full_name(self):
        return f"{self.first} {self.last}"

    def return_description(self):
        return (f"{self.first} {self.last} is {self.age} years old and "
                f"has a pay of {self.pay} with per annum increase of {self.pay_rate_increase}")

    def return_email_address(self):
        return f"{self.first}.{self.last}@company.com"

    @classmethod
    def set_raise_amt(cls, raise_rate):
        cls.pay_rate_increase = raise_rate
        print(f"Pay rate increased to {cls.pay_rate_increase}")


george = Profile("George", "Ahmed", 16, "Male", 500000)
zihan = Profile("Zihan", "Zamee-Khan", 17, "Male", 700000)


class Developer(Profile):
    def __init__(self, first, last, age, gender, pay, prog_lang):
        super().__init__(first, last, age, gender, pay)
        self.prog_lang = prog_lang


jason = Developer("Jason", "Smith", 18, "Female", 10000000, "Python")
print(jason+zihan)
