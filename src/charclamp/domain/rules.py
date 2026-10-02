"""炭窑焖烧志业务规则。"""

from __future__ import annotations

from charclamp.domain.models import BurnShift, Clamp

MIN_PEAK_TEMP_FOR_DRAWN = 400.0


class RuleError(ValueError):
    """业务规则校验失败。"""


def latest_shift_for_clamp(clamp: Clamp) -> BurnShift | None:
    if not clamp.shifts:
        return None
    return max(clamp.shifts, key=lambda s: s.started_at)


def has_open_peak_shift(clamp: Clamp) -> bool:
    """该窑是否存在峰值温度仍为空（未测峰值、焖烧中）的班次。"""
    return any(shift.peak_temp_c is None for shift in clamp.shifts)


def assert_can_open_shift(clamp: Clamp) -> None:
    """
    再开焖烧班次的前提：该窑当前不得有峰值为空的班次。
    一口窑同时最多一条「未测峰值」的焖烧班次。
    """
    if has_open_peak_shift(clamp):
        latest = latest_shift_for_clamp(clamp)
        when = latest.started_at.strftime("%Y-%m-%d %H:%M") if latest else ""
        tail = f"（{when} 开的班仍未测峰值）" if when else ""
        raise RuleError(
            f"窑 {clamp.code} 已有一条峰值未测的焖烧班次{tail}，"
            "禁止再开新班；请先补测该班峰值温度后再开。"
        )


def can_mark_clamp_drawn(clamp: Clamp) -> tuple[bool, str]:
    """
    炭窑转为「已出炭」(drawn) 的前提：
    最近一条焖烧班次的峰值温度已记录，且 >= 400℃。
    """
    latest = latest_shift_for_clamp(clamp)
    if latest is None:
        return False, "该窑尚无焖烧班次，不能标记为已出炭"
    if latest.peak_temp_c is None:
        return False, "最近班次尚未记录峰值温度，不能标记为已出炭"
    if latest.peak_temp_c < MIN_PEAK_TEMP_FOR_DRAWN:
        return (
            False,
            f"最近班次峰值温度 {latest.peak_temp_c}℃ 低于 {MIN_PEAK_TEMP_FOR_DRAWN:.0f}℃，不能标记为已出炭",
        )
    return True, ""


def assert_can_set_clamp_status(clamp: Clamp, new_status: str) -> None:
    allowed = {Clamp.STATUS_STACKED, Clamp.STATUS_BURNING, Clamp.STATUS_DRAWN}
    if new_status not in allowed:
        raise RuleError(f"无效状态：{new_status}")
    if new_status == Clamp.STATUS_DRAWN:
        ok, msg = can_mark_clamp_drawn(clamp)
        if not ok:
            raise RuleError(msg)
