import warnings

import numpy as np
import scipy.ndimage as ndi
from skimage.util.dtype import dtype_range

from .plotplugin import PlotPlugin
from ..canvastools import ThickLineTool


__all__ = ['LineProfile']


class LineProfile(PlotPlugin):
    """Plugin to compute interpolated intensity under a scan line on an image.

    See PlotPlugin and Plugin classes for additional details.

    Parameters
    ----------
    maxdist : float
        Maximum pixel distance allowed when selecting end point of scan line.
    epsilon : float
        Deprecated. Use `maxdist` instead.
    limits : tuple or {None, 'image', 'dtype'}
        (minimum, maximum) intensity limits for plotted profile. The following
        special values are defined:

            None : rescale based on min/max intensity along selected scan line.
            'image' : fixed scale based on min/max intensity in image.
            'dtype' : fixed scale based on min/max intensity of image dtype.
    """
    name = 'Line Profile'

    def __init__(self, maxdist=10, epsilon='deprecated',
                 limits='image', **kwargs):
        super(LineProfile, self).__init__(**kwargs)

        if not epsilon == 'deprecated':
            warnings.warn("Parameter `epsilon` deprecated; use `maxdist`.")
            maxdist = epsilon
        self.maxdist = maxdist
        self._limit_type = limits
        print(self.help())

    def attach(self, image_viewer):
        super(LineProfile, self).attach(image_viewer)

        image = image_viewer.original_image

        if self._limit_type == 'image':
            self.limits = (np.min(image), np.max(image))
        elif self._limit_type == 'dtype':
            self._limit_type = dtype_range[image.dtype.type]
        elif self._limit_type is None or len(self._limit_type) == 2:
            self.limits = self._limit_type
        else:
            raise ValueError("Unrecognized `limits`: %s" % self._limit_type)

        if not self._limit_type is None:
            self.ax.set_ylim(self.limits)

        h, w = image.shape[0:2]
        x = [w / 3, 2 * w / 3]
        y = [h / 2] * 2

        self.line_tool = ThickLineTool(self.image_viewer.ax,
                                       maxdist=self.maxdist,
                                       on_move=self.line_changed,
                                       on_change=self.line_changed)
        self.line_tool.end_points = np.transpose([x, y])

        scan_data = profile_line(image, self.line_tool.end_points)

        self.reset_axes(scan_data)

        self._autoscale_view()

    def help(self):
        helpstr = ("Line profile tool",
                   "+ and - keys or mouse scroll changes width of scan line.",
                   "Select and drag ends of the scan line to adjust it.")
        return '\n'.join(helpstr)

    def get_profile(self):
        """Return intensity profile of the selected line.

        Returns
        -------
        end_points: (2, 2) array
            The positions ((x1, y1), (x2, y2)) of the line ends.
        profile: 1d array
            Profile of intensity values.
        """
        profile = self.profile[0].get_ydata()
        return self.line_tool.end_points, profile

    def _autoscale_view(self):
        if self.limits is None:
            self.ax.autoscale_view(tight=True)
        else:
            self.ax.autoscale_view(scaley=False, tight=True)

    def line_changed(self, end_points):
        x, y = np.transpose(end_points)
        self.line_tool.end_points = end_points
        scan = profile_line(self.image_viewer.original_image, end_points,
                            linewidth=self.line_tool.linewidth)

        try:
            if scan[1].shape != len(self.profile):
                self.reset_axes(scan)
        except:
            self.reset_axes(scan)

        for i in range(len(scan[0])):
            self.profile[i].set_xdata(np.arange(scan.shape[0]))
            self.profile[i].set_ydata(scan[:, i])

        self.ax.relim()

        if self.useblit:
            self.ax.draw_artist(self.profile[0])

        self._autoscale_view()
        self.redraw()

    def reset_axes(self, scan_data):
        # Clear lines out
        for line in self.ax.lines:
            self.ax.lines = []

        if scan_data.shape[1] == 1:
            self.profile = self.ax.plot(scan_data, 'k-')
        else:
            self.profile = self.ax.plot(scan_data[:, 0], 'r-',
                                        scan_data[:, 1], 'g-',
                                        scan_data[:, 2], 'b-')


def profile_line(img, end_points, linewidth=1):
    """Return the intensity profile of an image measured along a scan line.

    Parameters
    ----------
    img : 2d array
        The image.
    end_points: (2, 2) list
        End points ((x1, y1), (x2, y2)) of scan line.
    linewidth: int
        Width of the scan, perpendicular to the line

    Returns
    -------
    return_value : array
        The intensity profile along the scan line. The length of the profile
        is the ceil of the computed length of the scan line.
    """
    point1, point2 = end_points
    x1, y1 = point1 = np.asarray(point1, dtype=float)
    x2, y2 = point2 = np.asarray(point2, dtype=float)
    dx, dy = point2 - point1

    # Quick calculation if perfectly horizontal or vertical
    if x1 == x2:
        if img.ndim == 2:
            pixels = img[min(y1, y2): max(y1, y2) + 1,
                         x1 - linewidth / 2: x1 + linewidth / 2 + 1]
            return pixels.mean(axis=1)[:, np.newaxis]
        else:
            for i in range(3):
                try:
                    temp = img[min(y1, y2): max(y1, y2) + 1,
                               x1 - linewidth / 2: x1 + linewidth / 2 + 1, i]
                    pixels = np.concatenate((pixels, temp[..., np.newaxis]),
                                            axis=2)
                    del temp
                except:
                    pixels = img[min(y1, y2): max(y1, y2) + 1,
                                 x1 - linewidth / 2: x1 + linewidth / 2 + 1,
                                 i][..., np.newaxis]
            return pixels.mean(axis=1)

    elif y1 == y2:
        if img.ndim == 2:
            pixels = img[y1 - linewidth / 2: y1 + linewidth / 2 + 1,
                         min(x1, x2): max(x1, x2) + 1]
            return pixels.mean(axis=1)[..., np.newaxis]
        else:
            for i in range(3):
                try:
                    temp = img[y1 - linewidth / 2: y1 + linewidth / 2 + 1,
                               min(x1, x2): max(x1, x2) + 1, i]
                    pixels = np.concatenate((pixels, temp[..., np.newaxis]),
                                            axis=2)
                    del temp
                except:
                    pixels = img[y1 - linewidth / 2: y1 + linewidth / 2 + 1,
                                 min(x1, x2): max(x1, x2) + 1,
                                 i][..., np.newaxis]
            return pixels.mean(axis=0)

    theta = np.arctan2(dy, dx)
    a = dy / dx
    b = y1 - a * x1
    length = np.hypot(dx, dy)

    line_x = np.linspace(min(x1, x2), max(x1, x2), np.ceil(length))
    line_y = line_x * a + b
    y_width = abs(linewidth * np.cos(theta) / 2)
    perp_ys = np.array([np.linspace(yi - y_width,
                                    yi + y_width, linewidth) for yi in line_y])
    perp_xs = - a * perp_ys + (line_x + a * line_y)[:, np.newaxis]

    perp_lines = np.array([perp_ys, perp_xs])
    if img.ndim == 3:
        pixels = np.zeros((perp_lines.shape[1], y_width * 2 + 1, 3))
        for i in range(3):
            pixels[..., i] = ndi.map_coordinates(img[..., i], perp_lines)
    else:
        pixels = ndi.map_coordinates(img, perp_lines)
        pixels = pixels[..., np.newaxis]

    intensities = pixels.mean(axis=1)

    if intensities.ndim == 1:
        return intensities[..., np.newaxis]
    else:
        return intensities
