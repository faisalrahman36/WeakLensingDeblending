#!/usr/bin/env python

"""Create plots to illustrate galaxy parameter error estimation using Fisher matrices.
"""

import argparse

import numpy as np

import matplotlib.pyplot as plt

import descwl

def main():
    # Initialize and parse command-line arguments.
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--verbose', action = 'store_true',
        help = 'Provide verbose output.')
    descwl.output.Reader.add_args(parser)
    parser.add_argument('--no-display', action = 'store_true',
        help = 'Do not display the image on screen.')
    parser.add_argument('-o','--output-name',type = str, default = None, metavar = 'FILE',
        help = 'Name of the output file to write.')
    parser.add_argument('--galaxy', type = int,
        default = None, metavar = 'ID',
        help = 'Use the galaxy with this database ID, ignoring any overlaps.')
    parser.add_argument('--group', type = int,
        default = None, metavar = 'ID',
        help = 'Use the overlapping group of galaxies with this group ID.')
    parser.add_argument('--partials', action = 'store_true',
        help = 'Show partial derivative images (instead of Fisher matrix images).')

    display_group = parser.add_argument_group('Display options')
    display_group.add_argument('--figure-size', type = float,
        default = 12., metavar = 'SIZE',
        help = 'Size of the longest edge of the figure in inches.')
    display_group.add_argument('--colormap', type = str,
        default = 'RdBu', metavar = 'CMAP',
        help = 'Matplotlib colormap name to use.')

    args = parser.parse_args()
    if args.no_display and not args.output_name:
        print 'No display our output requested.'
        return 0
    if args.galaxy is None and args.group is None:
        print 'Must specify either a galaxy or a group.'
        return -1
    if args.galaxy is not None and args.group is not None:
        print 'Cannot specify both a galaxy and a group.'
        return -1

    # Load the analysis results file we will get partial derivative images from.
    try:
        reader = descwl.output.Reader.from_args(args)
        results = reader.results
        labels = results.slice_labels
        npartials = len(labels)
        if args.verbose:
            print results.survey.description()
    except RuntimeError,e:
        print str(e)
        return -1

    # Look for the selected galaxy or group.
    if args.galaxy:
        selected = results.select('db_id==%d' % args.galaxy)
        if not np.any(selected):
            print 'No such galaxy with ID %d' % args.galaxy
            return -1
        title = 'galaxy-%d' % args.galaxy
    else:
        selected = results.select('grp_id==%d' % args.group)
        if not np.any(selected):
            print 'No such group with ID %d' % args.group
            return -1
        title = 'group-%d' % args.group
    selected = np.arange(results.num_objects)[selected]

    # Get the Fisher-matrix images for the selcted objects.
    fisher_images = results.get_fisher_images(selected)
    nrows,ncols,height,width = fisher_images.shape

    # Calculate the bounds for our figure.
    if args.partials:
        nrows = 1
    figure_scale = args.figure_size/(ncols*max(height,width))
    figure_width = ncols*width*figure_scale
    figure_height = nrows*height*figure_scale
    figure = plt.figure(figsize = (figure_width,figure_height),frameon = False)
    figure.canvas.set_window_title(title)
    plt.subplots_adjust(left = 0,bottom = 0,right = 1,top = 1,wspace = 0,hspace = 0)

    def draw(row,col,pixels):
        vcut = np.max(np.fabs(np.percentile(pixels[pixels != 0],(10,90))))
        scaled = np.clip(pixels,-vcut,+vcut)
        axes = plt.subplot(nrows,ncols,row*ncols+col+1)
        axes.set_axis_off()
        plt.imshow(scaled,origin = 'lower',interpolation = 'nearest',
            cmap = args.colormap,vmin = -vcut,vmax = +vcut)

    if args.partials:
        stamp1 = results.get_subimage(selected)
        for index1 in range(ncols):
            galaxy1 = selected[index1//npartials]
            slice1 = index1%npartials
            stamp1.array[:] = 0.
            stamp1[results.bounds[galaxy1]] = results.get_stamp(galaxy1,slice1)
            if slice1 == 0:
                # Normalize to give partial with respect to added flux in electrons.
                stamp1 /= results.table['flux'][galaxy1]
            draw(0,index1,stamp1.array)
    else:
        for index1 in range(ncols):
            for index2 in range(index1+1):
                fisher_image = fisher_images[index1,index2]
                if np.count_nonzero(fisher_image) > 0:
                    draw(index1,index2,fisher_image)        

    if args.output_name:
        figure.savefig(args.output_name)

    if not args.no_display:
        plt.show()

if __name__ == '__main__':
    main()
