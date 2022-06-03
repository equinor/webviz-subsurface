import numpy as np


def rdp(points, epsilon=5):
    # https://towardsdatascience.com/simplify-polylines-with-the-douglas-peucker-algorithm-ac8ed487a4a1
    # get the start and end points

    start = np.tile(np.expand_dims(points[0], axis=0), (points.shape[0], 1))
    end = np.tile(np.expand_dims(points[-1], axis=0), (points.shape[0], 1))
    # find distance from other_points to line formed by start and end
    dist_point_to_line = np.abs(
        np.cross(end - start, points - start, axis=-1)
    ) / np.linalg.norm(end - start, axis=-1)
    # get the index of the points with the largest distance
    max_idx = np.argmax(dist_point_to_line)
    max_value = dist_point_to_line[max_idx]

    result = []
    if max_value > epsilon:
        partial_results_left = rdp(points[: max_idx + 1], epsilon)
        result += [list(i) for i in partial_results_left if list(i) not in result]
        partial_results_right = rdp(points[max_idx:], epsilon)
        result += [list(i) for i in partial_results_right if list(i) not in result]
    else:
        result += [points[0], points[-1]]

    return result
