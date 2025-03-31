prime_array = bytes(
    [
        188,
        223,
        9,
        149,
        64,
        85,
        250,
        187,
        46,
        43,
        7,
        141,
        98,
        242,
        217,
        92,
        165,
        224,
        181,
        233,
        215,
        8,
        78,
        218,
        132,
        92,
        205,
        217,
        68,
        104,
        156,
        149,
        203,
        154,
        98,
        135,
        113,
        216,
        27,
        127,
        182,
        178,
        20,
        77,
        55,
        90,
        35,
        34,
        177,
        253,
        33,
        129,
        91,
        152,
        221,
        91,
        175,
        206,
        119,
        211,
        228,
        153,
        125,
        219,
        231,
        255,
        207,
        84,
        23,
        31,
        124,
        216,
        95,
        207,
        228,
        144,
        74,
        114,
        60,
        44,
        139,
        192,
        167,
        89,
        9,
        227,
        100,
        155,
        200,
        81,
        121,
        8,
        33,
        189,
        116,
        50,
        127,
        62,
        60,
        127,
        250,
        195,
        25,
        252,
        112,
        172,
        137,
        183,
        213,
        2,
        207,
        49,
        161,
        185,
        65,
        211,
        21,
        44,
        233,
        188,
        143,
        13,
        44,
        78,
        62,
        78,
        234,
        115,
    ]
)
prime_bytes = bytes(prime_array)
prime_int = int.from_bytes(prime_bytes, byteorder="big")
