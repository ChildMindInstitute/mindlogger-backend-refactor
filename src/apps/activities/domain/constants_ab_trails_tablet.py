from apps.activities.domain.ab_trails_base import ABTrailsNodes, ABTrailsTutorial, Node, Tutorial

TABLET_NODES_FIRST: ABTrailsNodes = ABTrailsNodes(
    radius=4.18,
    font_size=5.6,
    font_size_begin_end=3,
    begin_word_length=7.8,
    end_word_length=6,
    nodes=[
        Node(order_index=1, cx=47.76, cy=59.7, label="1"),
        Node(order_index=2, cx=59.7, cy=38.5, label="2"),
        Node(order_index=3, cx=79.4, cy=60.89, label="3"),
        Node(order_index=4, cx=64.17, cy=51.94, label="4"),
        Node(order_index=5, cx=65.67, cy=68.65, label="5"),
        Node(order_index=6, cx=23.88, cy=70.15, label="6"),
        Node(order_index=7, cx=20.9, cy=49.25, label="7"),
        Node(order_index=8, cx=41.79, cy=44.77, label="8"),
    ],
)

TABLET_NODES_SECOND: ABTrailsNodes = ABTrailsNodes(
    radius=3.2,
    font_size=3.6,
    font_size_begin_end=2.64,
    begin_word_length=7,
    end_word_length=4.8,
    nodes=[
        Node(order_index=1, cx=64.77, cy=58.2, label="1"),
        Node(order_index=2, cx=47.16, cy=72.23, label="2"),
        Node(order_index=3, cx=71.94, cy=76.12, label="3"),
        Node(order_index=4, cx=68.65, cy=37.31, label="4"),
        Node(order_index=5, cx=43.88, cy=41.19, label="5"),
        Node(order_index=6, cx=55.82, cy=49.25, label="6"),
        Node(order_index=7, cx=41.19, cy=59.7, label="7"),
        Node(order_index=8, cx=28.36, cy=77.61, label="8"),
        Node(order_index=9, cx=33.13, cy=88.66, label="9"),
        Node(order_index=10, cx=39.1, cy=76.72, label="10"),
        Node(order_index=11, cx=61.19, cy=91.64, label="11"),
        Node(order_index=12, cx=20.3, cy=96.12, label="12"),
        Node(order_index=13, cx=26.86, cy=49.55, label="13"),
        Node(order_index=14, cx=18.21, cy=62.69, label="14"),
        Node(order_index=15, cx=17.61, cy=9.25, label="15"),
        Node(order_index=16, cx=26.86, cy=25.37, label="16"),
        Node(order_index=17, cx=50.75, cy=5.97, label="17"),
        Node(order_index=18, cx=47.76, cy=29.25, label="18"),
        Node(order_index=19, cx=72.84, cy=14.93, label="19"),
        Node(order_index=20, cx=58.81, cy=15.22, label="20"),
        Node(order_index=21, cx=79.7, cy=4.77, label="21"),
        Node(order_index=22, cx=80, cy=35.22, label="22"),
        Node(order_index=23, cx=82.09, cy=93.43, label="23"),
        Node(order_index=24, cx=77.91, cy=55.22, label="24"),
        Node(order_index=25, cx=74.03, cy=90.45, label="25"),
    ],
)

TABLET_NODES_THIRD: ABTrailsNodes = ABTrailsNodes(
    radius=4.88,
    font_size=5.6,
    font_size_begin_end=3,
    begin_word_length=7.8,
    end_word_length=5.4,
    nodes=[
        Node(order_index=1, cx=44.78, cy=59.7, label="1"),
        Node(order_index=2, cx=62.09, cy=31.34, label="A"),
        Node(order_index=3, cx=83.28, cy=59.4, label="2"),
        Node(order_index=4, cx=63.88, cy=45.37, label="B"),
        Node(order_index=5, cx=63.88, cy=73.43, label="3"),
        Node(order_index=6, cx=20.6, cy=73.73, label="C"),
        Node(order_index=7, cx=13.43, cy=33.13, label="4"),
        Node(order_index=8, cx=37.91, cy=42.09, label="D"),
    ],
)

TABLET_NODES_FOURTH: ABTrailsNodes = ABTrailsNodes(
    radius=3.2,
    font_size=3.6,
    font_size_begin_end=2.64,
    begin_word_length=7,
    end_word_length=4.8,
    nodes=[
        Node(order_index=1, cx=48.36, cy=44.48, label="1"),
        Node(order_index=2, cx=64.78, cy=71.04, label="A"),
        Node(order_index=3, cx=31.94, cy=80.9, label="2"),
        Node(order_index=4, cx=43.28, cy=18.81, label="B"),
        Node(order_index=5, cx=44.78, cy=32.84, label="3"),
        Node(order_index=6, cx=62.09, cy=55.82, label="C"),
        Node(order_index=7, cx=51.94, cy=15.82, label="4"),
        Node(order_index=8, cx=72.24, cy=12.53, label="D"),
        Node(order_index=9, cx=72.24, cy=46.87, label="5"),
        Node(order_index=10, cx=75.22, cy=86.57, label="E"),
        Node(order_index=11, cx=44.18, cy=81.79, label="6"),
        Node(order_index=12, cx=25.37, cy=89.25, label="F"),
        Node(order_index=13, cx=33.73, cy=43.58, label="7"),
        Node(order_index=14, cx=25.07, cy=63.58, label="G"),
        Node(order_index=15, cx=21.19, cy=17.01, label="8"),
        Node(order_index=16, cx=24.78, cy=51.64, label="H"),
        Node(order_index=17, cx=33.13, cy=11.94, label="9"),
        Node(order_index=18, cx=60.9, cy=10.75, label="I"),
        Node(order_index=19, cx=81.49, cy=5.97, label="10"),
        Node(order_index=20, cx=75.82, cy=71.64, label="J"),
        Node(order_index=21, cx=80.6, cy=93.13, label="11"),
        Node(order_index=22, cx=16.41, cy=94.33, label="K"),
        Node(order_index=23, cx=16.12, cy=61.19, label="12"),
        Node(order_index=24, cx=20.9, cy=82.99, label="L"),
        Node(order_index=25, cx=18.21, cy=7.16, label="13"),
    ],
)

TABLET_TUTORIALS_FIRST: ABTrailsTutorial = ABTrailsTutorial(
    tutorials=[
        Tutorial(text="There are numbers in circles on this screen."),
        Tutorial(text="You will take a pen and draw a line from one number to the next, in order."),
        Tutorial(text="Start at 1.", node_label="1"),
        Tutorial(text="Then go to 2.", node_label="2"),
        Tutorial(text="Then 3, and so on.", node_label="3"),
        Tutorial(
            text="Please try not to lift the pen as you move from one number to the next. Work as quickly as you can."
        ),
        Tutorial(text="Begin here.", node_label="1"),
        Tutorial(text="And end here.", node_label="8"),
        Tutorial(text="Click next to start"),
    ],
)

TABLET_TUTORIALS_SECOND: ABTrailsTutorial = ABTrailsTutorial(
    tutorials=[
        Tutorial(text="On this screen are more numbers in circles."),
        Tutorial(text="You will take a pen and draw a line from one circle to the next, in order."),
        Tutorial(text="Start at 1.", node_label="1"),
        Tutorial(text="And End here.", node_label="25"),
        Tutorial(text="Please try not to lift the pen as you move from one circle to the next."),
        Tutorial(text="Work as quickly as you can."),
        Tutorial(
            text="Click next to start",
        ),
    ],
)

TABLET_TUTORIALS_THIRD: ABTrailsTutorial = ABTrailsTutorial(
    tutorials=[
        Tutorial(text="There are numbers and letters in circles on this screen."),
        Tutorial(text="You will take a pen and draw a line alternating in order between the numbers and letters."),
        Tutorial(text="Start at number 1.", node_label="1"),
        Tutorial(text="Then go to the first letter A.", node_label="A"),
        Tutorial(text="Then go to the next number 2.", node_label="2"),
        Tutorial(text="Then go to the next letter B, and so on.", node_label="B"),
        Tutorial(
            text="Please try not to lift the pen as you move from one number to the next. Work as quickly as you can."
        ),
        Tutorial(text="Begin here.", node_label="1"),
        Tutorial(text="And end here.", node_label="D"),
        Tutorial(
            text="Click next to start",
        ),
    ],
)

TABLET_TUTORIALS_FOURTH: ABTrailsTutorial = ABTrailsTutorial(
    tutorials=[
        Tutorial(text="On this screen there are more numbers and letters in circles."),
        Tutorial(text="You will take a pen and draw a line from one circle to the next."),
        Tutorial(text="Alternating in order between the numbers and letters."),
        Tutorial(text="Start at 1.", node_label="1"),
        Tutorial(text="And end here.", node_label="13"),
        Tutorial(text="Please try not to lift the pen as you move from one circle to the next."),
        Tutorial(text="Work as quickly as you can."),
        Tutorial(
            text="Click next to start",
        ),
    ],
)
