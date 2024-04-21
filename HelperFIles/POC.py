import numpy as np
import matplotlib.pyplot as plt


# def calc_angles(a, b, c):
#     alpha = np.arccos((b**2 + c**2 - a**2) / (2.*b*c))
#     beta = np.arccos((-b**2 + c**2 + a**2) / (2.*a*c))
#     gamma = np.pi-alpha-beta
#     return alpha, beta, gamma


# def calc_point(alpha, beta, c):
#     x = (c*np.tan(beta))/(np.tan(alpha)+np.tan(beta))
#     y = x * np.tan(alpha)
#     return (x, y)


# def get_triangle(a, b, c):
#     z = np.array([a, b, c])
#     while z[-1] != z.max():
#         z = z[[2, 0, 1]]  # make sure last entry is largest
#     alpha, beta, _ = calc_angles(*z)
#     x, y = calc_point(alpha, beta, z[-1])
#     return [(0, 0), (z[-1], 0), (x, y)]


# a = 4
# b = 3
# c = 2

# fig, ax = plt.subplots()
# ax.set_aspect("equal")

# dreieck = plt.Polygon(get_triangle(a, b, c))
# ax.add_patch(dreieck)
# ax.relim()
# ax.autoscale_view()
# plt.show()

# plt.plot(6, -7, marker = 'o', color = 'yellow')
plt.plot(11, -7, marker='o', color='black')
plt.plot(3.5, -1, marker='o', color='green')

plt.plot(
    [6, 11, 3.5, 6],
    [-7, -7, -1, -7]
)
plt.fill(
    [6, 11, 3.5, 6],
    [-7, -7, -1, -7],
    color='#fa2942'
)
angles = linspace(0, 2/4 * pi, 25)
x = cos(angles)
y = sin(angles)
plt.plot(x + 5.5, y - 7, color='black')


plt.title("Types of Triangles", color='#e33f4b', fontsize=20)
plt.xlim(-10, 12)
plt.ylim(-10, 12)
plt.show()
