import random
from typing import Tuple

class BetTypes:
    SINGLE = 'single'
    DOZEN = 'dozen'
    COLOR = 'color'
    ODD_EVEN = 'odd_even'
    HALF = 'half'

payouts = {
    BetTypes.SINGLE: 35,
    BetTypes.DOZEN: 2,
    BetTypes.COLOR: 1,
    BetTypes.ODD_EVEN: 1,
    BetTypes.HALF: 1
}

european_wheel_values = {
    0 : 'green', 32 : 'red',  15 : 'black', 19 : 'red',
    4 : 'black', 21 : 'red', 2 : 'black', 25 : 'red',
    17 : 'black', 34 : 'red', 6 : 'black', 27 : 'red',
    13 : 'black', 36 : 'red', 11 : 'black', 30 : 'red',
    8 : 'black', 23 : 'red', 10 : 'black', 5 : 'red',
    24 : 'black', 16 : 'red', 33 : 'black', 1 : 'red',
    20 : 'black', 14 : 'red', 31 : 'black', 9 : 'red',
    22 : 'black', 18 : 'red', 29 : 'black', 7 : 'red',
    28 : 'black', 12 : 'red', 35 : 'black', 3 : 'red',
    26 : 'black'
}

american_wheel_values = {
    0 : 'green', 28 : 'black', 9 : 'red', 26 : 'black',
    30 : 'red', 11 : 'black', 7 : 'red', 20 : 'black',
    32 : 'red', 17 : 'black', 5 : 'red', 22 : 'black',
    34 : 'red', 15 : 'black', 3 : 'red', 24 : 'black',
    36 : 'red', 13 : 'black', 1 : 'red', 00: 'green',
    27 : 'black', 10 : 'red', 25 : 'black', 29 : 'red',
    12 : 'black', 8 : 'red', 19 : 'black', 31 : 'red',
    18 : 'black', 6 : 'red', 21 : 'black', 33 : 'red',
    16 : 'black', 4 : 'red', 23 : 'black'
}
    
class Bet:
    def __init__(self, bet_type, bet_value, amount, type='european'):
        self.bet_type = bet_type
        self.bet_value = bet_value
        self.amount = amount

        self.validate_bet()

    def validate_bet(self):
        # Validate bet type
        if self.bet_type not in payouts:
            raise ValueError(f"Invalid bet type: {self.bet_type} - must be one of {list(payouts.keys())}")
             
        # Validate bet value based on bet type
        if self.bet_type == BetTypes.SINGLE:
            if not (0 <= int(self.bet_value) <= self.wheel):
                raise ValueError("For SINGLE bets, bet_value must be an integer between 0 and 36.")
        elif self.bet_type == BetTypes.DOZEN:
            if self.bet_value not in ['1', '2', '3']:
                raise ValueError("For DOZEN bets, bet_value must be '1', '2', or '3'.") 
        elif self.bet_type == BetTypes.COLOR:
            if self.bet_value not in ['red', 'black']:
                raise ValueError("For COLOR bets, bet_value must be 'red' or 'black'.")
        elif self.bet_type == BetTypes.ODD_EVEN:
            if self.bet_value not in ['odd', 'even']:
                raise ValueError("For ODD_EVEN bets, bet_value must be 'odd' or 'even'.")
        elif self.bet_type == BetTypes.HALF:
            if self.bet_value not in ['1', '2']:
                raise ValueError("For HALF bets, bet_value must be '1' or '2'.")

        return True

class SpinResult:
    def __init__(self, number, color):
        self.number = number
        self.color = color

class Roulette:
    def  __init__(self, type='european', seed=-1):
        if type == 'european':
            self.wheel = european_wheel_values 
        elif type == 'american':
            self.wheel = american_wheel_values

        if seed == -1:
            random.seed()
        else:
            random.seed(seed)

    def spin(self, bet : Bet) -> Tuple[int, int, str]:
        number_result = random.choice(list(self.wheel.keys()))
        payout = self.determine_payout(bet, number_result)

        return payout, number_result, self.wheel[number_result]

    def determine_payout(self, bet : Bet, number_result):
        color_result = self.wheel[number_result]

        if bet.bet_type == BetTypes.SINGLE:
            if bet.bet_value == number_result:
                return bet.amount * payouts[BetTypes.SINGLE]
        elif bet.bet_type == BetTypes.DOZEN:
            if ((bet.bet_value == 1 and 1 <= number_result <= 12) or # First Dozen
                (bet.bet_value == 2 and 13 <= number_result <= 24) or # Second Dozen
                (bet.bet_value == 3 and 25 <= number_result <= 36)): # Third Dozen
                return bet.amount * payouts[BetTypes.DOZEN]
        elif bet.bet_type == BetTypes.COLOR:
            if bet.bet_value == color_result:
                return bet.amount * payouts[BetTypes.COLOR]
        elif bet.bet_type == BetTypes.ODD_EVEN:
            if (   (bet.bet_value == 'odd' and number_result % 2 == 1)  # Odd
                or (bet.bet_value == 'even' and number_result % 2 == 0)): # Even
                return bet.amount * payouts[BetTypes.ODD_EVEN]
        elif bet.bet_type == BetTypes.HALF:
            if ((bet.bet_value == 1 and 1 <= number_result <= 18) or # First Half
                (bet.bet_value == 2 and 19 <= number_result <= 36)): # Second Half
                return bet.amount * payouts[BetTypes.HALF]
        
        return 0 # No payout