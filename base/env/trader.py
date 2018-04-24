# coding=utf-8

import math

from enum import Enum
from base.env.position import Position


class ActionCode(Enum):
    Buy = 0
    Hold = 1
    Sell = 2


class ActionStatus(Enum):
    Success = 0
    Failed = -1


class Trader(object):

    def __init__(self, market, cash=100000.0):
        # Init cash, market, codes.
        self.cash, self.market, self.codes = cash, market, market.codes

        # Init reward.
        self.reward = 0
        # Init holding positions.
        self.positions = []
        # Init action times.
        self.action_times = 0
        # Init initial cash.
        self.initial_cash = cash
        # Init total rewards.
        self.total_rewards = 0
        # Init current action code.
        self.cur_action_code = None
        # Init current action status.
        self.cur_action_status = None

        # Init history profits and baselines.
        self.history_profits = []
        self.history_baselines = []

        # Init action dic.
        self.action_dic = {ActionCode.Buy: self.buy, ActionCode.Hold: self.hold, ActionCode.Sell: self.sell}

    @property
    def codes_count(self):
        return len(self.codes)

    @property
    def action_space(self):
        return self.codes_count * 3

    @property
    def profits(self):
        return self.cash + self.holdings_value - self.initial_cash

    @property
    def holdings_value(self):
        holdings_value = 0
        # Accumulate position value.
        for position in self.positions:
            holdings_value += position.cur_value
        return holdings_value

    def buy(self, code, stock, amount, stock_next):
        # Check if amount is valid.
        amount = amount if self.cash > stock.close * amount else int(math.floor(self.cash / stock.close))
        # If amount > 0, means cash is enough.
        if amount > 0:
            # Check if position exists.
            if not self._exist_position(code):
                # Build position if possible.
                position = Position(code, stock.close, amount, stock_next.close)
                self.positions.append(position)
            else:
                # Get position and update if possible.
                position = self._position(code)
                position.add(stock.close, amount, stock_next.close)
            # Update cash and holding price.
            self.cash -= amount * stock.close
            self._update_reward(ActionCode.Buy, ActionStatus.Success, position)
            self.market.logger.info("Code: {0},"
                                    " buy success,"
                                    " cash: {1:.2f},"
                                    " holding value:{2:.2f}".format(code,
                                                                    self.cash,
                                                                    self.holdings_value))
        else:
            self.market.logger.info("Code: {}, not enough cash, cannot buy.".format(code))
            if self._exist_position(code):
                # If position exists, update status.
                position = self._position(code)
                position.update_status(stock.close, stock_next.close)
                self._update_reward(ActionCode.Buy, ActionStatus.Failed, position)

    def sell(self, code, stock, amount, stock_next):
        # Check if position exists.
        if not self._exist_position(code):
            self.market.logger.info("Code: {}, not exists in Positions, sell failed.".format(code))
            return self._update_reward(ActionCode.Sell, ActionStatus.Failed, None)
        # Sell position if possible.
        position = self._position(code)
        amount = amount if amount < position.amount else position.amount
        position.sub(stock.close, amount, stock_next.close)
        # Update cash and holding price.
        self.cash += amount * stock.close
        self._update_reward(ActionCode.Sell, ActionStatus.Success, position)
        self.market.logger.info("Code: {0},"
                                " sell success,"
                                " cash: {1:.2f},"
                                " holding value:{2:.2f}".format(code,
                                                                self.cash,
                                                                self.holdings_value))

    def hold(self, code, stock, _, stock_next):
        if not self._exist_position(code):
            self.market.logger.info("Code: {}, not exists in Positions, hold failed.".format(code))
            return self._update_reward(ActionCode.Hold, ActionStatus.Failed, None)
        position = self._position(code)
        position.update_status(stock.close, stock_next.close)
        self._update_reward(ActionCode.Hold, ActionStatus.Success, position)
        self.market.logger.info("Code: {0},"
                                " hold success,"
                                " cash: {1:.2f},"
                                " holding value:{2:.2f}".format(code,
                                                                self.cash,
                                                                self.holdings_value))

    def reset(self):
        self.cash = self.initial_cash
        self.positions = []
        self.history_profits = []
        self.history_baselines = []
        self.total_rewards = 0

    def reset_reward(self):
        self.reward = 0

    def action_by_code(self, code):
        return self.action_dic[ActionCode(code)]

    def remove_invalid_positions(self):
        self.positions = [position for position in self.positions if position.amount > 0]

    def log_asset(self, episode):
        self.market.logger.warning(
            "Episode: {0} | "
            "Cash: {1:.2f} | "
            "Holdings: {2:.2f} | "
            "Profits: {3:.2f} | "
            "Rewards: {4:.2f}".format(episode, self.cash, self.holdings_value, self.profits, self.total_rewards)
        )

    def _update_reward(self, action_code, action_status, position):
        self.reward = self._calculate_reward_v2(action_code, action_status, position)
        self.total_rewards += self.reward
        self.cur_action_code = action_code
        self.cur_action_status = action_status

    def _exist_position(self, code):
        return True if len([position.code for position in self.positions if position.code == code]) else False

    def _position(self, code):
        return [position for position in self.positions if position.code == code][0]

    @staticmethod
    def _calculate_reward_v1(action_code, action_status, position):
        if action_status == ActionStatus.Failed:
            reward = -100
        else:
            if position.pro_value >= position.cur_value:
                if action_code == ActionCode.Hold:
                    reward = 50
                else:
                    reward = 100
            else:
                reward = - 50
        return reward

    @staticmethod
    def _calculate_reward_v2(_, action_status, position):
        if action_status == ActionStatus.Success:
            reward = position.pro_value - position.cur_value
        else:
            reward = -200
        return reward
