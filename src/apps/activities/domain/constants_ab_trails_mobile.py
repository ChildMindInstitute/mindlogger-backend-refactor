from apps.activities.domain.ab_trails_base import ABTrailsNodes, ABTrailsTutorial, Node, Tutorial

MOBILE_NODES_FIRST: ABTrailsNodes = ABTrailsNodes(
    radius=4.18,
    font_size=5.6,
    nodes=[
        Node(order_index=1, cx=52.24, cy=11.94, label="1"),
        Node(order_index=2, cx=85.07, cy=17.91, label="2"),
        Node(order_index=3, cx=88.06, cy=74.63, label="3"),
        Node(order_index=4, cx=53.73, cy=86.57, label="4"),
        Node(order_index=5, cx=77.61, cy=40.3, label="5"),
        Node(order_index=6, cx=17.01, cy=38.81, label="6"),
        Node(order_index=7, cx=53.73, cy=56.72, label="7"),
        Node(order_index=8, cx=19.4, cy=79.1, label="8"),
        Node(order_index=9, cx=14.93, cy=59.7, label="9"),
        Node(order_index=10, cx=50.75, cy=31.34, label="10"),
        Node(order_index=11, cx=13.43, cy=14.93, label="11"),
    ],
)

MOBILE_NODES_SECOND: ABTrailsNodes = ABTrailsNodes(
    radius=4.18,
    font_size=5.97,
    nodes=[
        Node(order_index=1, cx=17.01, cy=38.81, label="1"),
        Node(order_index=2, cx=77.61, cy=40.3, label="2"),
        Node(order_index=3, cx=52.24, cy=11.94, label="3"),
        Node(order_index=4, cx=13.43, cy=14.93, label="4"),
        Node(order_index=5, cx=53.73, cy=56.72, label="5"),
        Node(order_index=6, cx=85.07, cy=17.91, label="6"),
        Node(order_index=7, cx=88.06, cy=74.63, label="7"),
        Node(order_index=8, cx=14.93, cy=59.7, label="8"),
        Node(order_index=9, cx=19.4, cy=79.1, label="9"),
        Node(order_index=10, cx=50.75, cy=31.34, label="10"),
        Node(order_index=11, cx=53.73, cy=86.57, label="11"),
    ],
)

MOBILE_NODES_THIRD: ABTrailsNodes = ABTrailsNodes(
    radius=4.18,
    font_size=5.97,
    nodes=[
        Node(order_index=1, cx=53.73, cy=86.57, label="1"),
        Node(order_index=2, cx=88.06, cy=74.63, label="A"),
        Node(order_index=3, cx=85.07, cy=17.91, label="2"),
        Node(order_index=4, cx=52.24, cy=11.94, label="B"),
        Node(order_index=5, cx=77.61, cy=40.3, label="3"),
        Node(order_index=6, cx=14.92, cy=59.7, label="C"),
        Node(order_index=7, cx=50.75, cy=31.34, label="4"),
        Node(order_index=8, cx=13.43, cy=14.92, label="D"),
        Node(order_index=9, cx=53.73, cy=56.72, label="5"),
        Node(order_index=10, cx=17.01, cy=38.81, label="E"),
        Node(order_index=11, cx=19.4, cy=79.1, label="6"),
    ],
)

MOBILE_NODES_FOURTH: ABTrailsNodes = ABTrailsNodes(
    radius=4.18,
    font_size=5.97,
    nodes=[
        Node(order_index=1, cx=50.75, cy=31.34, label="1"),
        Node(order_index=2, cx=13.43, cy=14.93, label="A"),
        Node(order_index=3, cx=52.24, cy=11.94, label="2"),
        Node(order_index=4, cx=17.01, cy=38.81, label="B"),
        Node(order_index=5, cx=77.61, cy=40.3, label="3"),
        Node(order_index=6, cx=85.07, cy=17.91, label="C"),
        Node(order_index=7, cx=88.06, cy=74.63, label="4"),
        Node(order_index=8, cx=14.93, cy=59.7, label="D"),
        Node(order_index=9, cx=53.73, cy=56.72, label="5"),
        Node(order_index=10, cx=19.4, cy=79.1, label="E"),
        Node(order_index=11, cx=53.73, cy=86.57, label="6"),
    ],
)

MOBILE_TUTORIALS_FIRST: ABTrailsTutorial = ABTrailsTutorial(
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
        Tutorial(text="And end here.", node_label="11"),
        Tutorial(text="Click next to start"),
    ],
)

MOBILE_TUTORIALS_SECOND: ABTrailsTutorial = ABTrailsTutorial(
    tutorials=[
        Tutorial(text="On this screen are more numbers in circles."),
        Tutorial(text="You will take a pen and draw a line from one circle to the next, in order."),
        Tutorial(text="Start at 1.", node_label="1"),
        Tutorial(text="And End here.", node_label="11"),
        Tutorial(text="Please try not to lift the pen as you move from one circle to the next."),
        Tutorial(text="Work as quickly as you can."),
        Tutorial(
            text="Click next to start",
        ),
    ],
)

MOBILE_TUTORIALS_THIRD: ABTrailsTutorial = ABTrailsTutorial(
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
        Tutorial(text="And end here.", node_label="6"),
        Tutorial(
            text="Click next to start",
        ),
    ],
)

MOBILE_TUTORIALS_FOURTH: ABTrailsTutorial = ABTrailsTutorial(
    tutorials=[
        Tutorial(text="On this screen there are more numbers and letters in circles."),
        Tutorial(text="You will take a pen and draw a line from one circle to the next."),
        Tutorial(text="Alternating in order between the numbers and letters."),
        Tutorial(text="Start at 1.", node_label="1"),
        Tutorial(text="And end here.", node_label="6"),
        Tutorial(text="Please try not to lift the pen as you move from one circle to the next."),
        Tutorial(text="Work as quickly as you can."),
        Tutorial(
            text="Click next to start",
        ),
    ],
)
