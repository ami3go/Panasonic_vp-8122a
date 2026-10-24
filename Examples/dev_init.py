"""Safe setup example. Does not switch on RF unless explicitly authorized."""
from panasonic_vp8122a import RFProfile, VP8122A


def rf_init(resource_name: str, *, authorize_rf_on: bool = False) -> None:
    with VP8122A(resource_name) as rf:
        # 0.531 MHz is 531 kHz, NOT 531 Hz.
        rf.configure(RFProfile(frequency_hz=531_000, level_dbuv=20.0,
                               impedance_ohm=50, am_depth_percent=30.0))
        if authorize_rf_on:
            rf.enable_output(authorized=True)
        # context manager attempts APOF during cleanup, but output is UNCONFIRMED.


if __name__ == '__main__':
    raise SystemExit('Call rf_init(resource_name) explicitly; see README for HIL cautions.')
