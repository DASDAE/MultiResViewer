
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates
from . import process
import dascore as dc
from glob import glob
import os

def _get_datetime(t):
    date = mdates.num2date(t)
    return np.datetime64(date.replace(tzinfo=None))

def _create_spool_list(raw_data_path, process_data_path):

    spools = []

    spools.append(dc.spool(raw_data_path))


    paths = glob(process_data_path+'/*')
    for i in range(1,len(paths)+1):
        datapath = os.path.join(process_data_path,str(i))
        if os.path.isdir(datapath):
            spools.append(dc.spool(datapath))
    
    return spools

class MultiResViewer:
    def __init__(self, raw_data_path, process_data_path, figsize=None,scale=None,
                 scale_type='relative',max_viz_size=200,
                 pre_process_for_raw = None):
        """
        Initializes a MultiResViewer instance.

        Parameters:
        - raw_data_path (str): The path to the raw data.
        - process_data_path (str): The path to the processed data.
        - figsize (tuple, optional): The size of the matplotlib figure (width, height).
        - scale (float, optional): The scale factor for the waterfall plot. Default is None.
        - scale_type (str, optional): The type of scaling ('relative' or 'absolute'). Default is 'relative'. 
                                        This parameter will be passed to dascore waterfall plot function.
        - max_viz_size (int, optional): The maximum size for visualization. Default is 200. In Mb.
        - pre_process_for_raw (function, optional): A function to preprocess raw data. Default is None.
        """
        self.spools = _create_spool_list(raw_data_path,process_data_path)
        self.zoom_points = []
        self.zoom_history = []
        self.max_size = max_viz_size
        self.fig, self.ax = plt.subplots(figsize=figsize)
        self.pre_process = pre_process_for_raw
        
        self.waiting_for_zoom = False
        self.waterfall_scale = scale
        self.waterfall_scale_type = scale_type
        self.change_scale = 0.2
        
        # Connect the functions to key press events
        self.fig.canvas.mpl_connect('key_press_event', self.handle_key_press)
        self.fig.canvas.mpl_connect('button_press_event', self.handle_mouse_click)
        
        self.initial_draw()
        
    def initial_draw(self):
        init_patch = self.spools[-1].chunk(time=None,tolerance=3)[0]
        self.data = init_patch
        self.draw()
        if len(self.zoom_history)>1:
            xlim, ylim = self.zoom_history[0]
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)
        self.fig.canvas.draw()
        
    def get_patch_data(self, bgtime, edtime):
        for i,sp in enumerate(self.spools):
            sp_size = process.estimate_spool_size(sp.select(time=(bgtime,edtime)))
            if sp_size <= self.max_size:
                DASdata = sp.select(time=(bgtime,edtime)).chunk(time=None,tolerance=3)[0]
                if (i==0) and (self.pre_process is not None):
                    DASdata = self.pre_process(DASdata)
                break
        return DASdata

    def handle_key_press(self, event):
        if event.key == 'x':
            print("Click another point to define the zoom range.")
            self.zoom_points = [] # Reset zoom_points for new zoom
            self.zoom_points.append((event.xdata, event.ydata))
            self.waiting_for_zoom = True 
        elif event.key == 'o':
            self.undo_zoom()
        elif event.key == 'O':
            self.initial_draw()
            self.zoom_history = []
        self.change_clim(event) # Handles clim changes

    def handle_mouse_click(self, event):
        if self.waiting_for_zoom == True:
            if len(self.zoom_points) < 2:
                self.zoom_points.append((event.xdata, event.ydata))
                if len(self.zoom_points) == 2:
                    self.waiting_for_zoom = False
                    self.perform_zoom()
    
    def _update_data(self, xlim, ylim):
        # update the patch data based on the selected time range
        if self.data.dims[0] == 'time':
            t1 = ylim[0]; t2 = ylim[1]
        else:
            t1 = xlim[0]; t2 = xlim[1]
        bgtime = _get_datetime(min(t1,t2))
        edtime = _get_datetime(max(t1,t2))
        
        self.data = self.get_patch_data(bgtime, edtime)
        self.draw()

    def perform_zoom(self):
        # Record the current zoom state
        self.zoom_history.append((self.ax.get_xlim(), self.ax.get_ylim()))
        
        # Get the points clicked by the user
        x1, x2 = self.zoom_points[0][0], self.zoom_points[1][0]
        y1, y2 = self.zoom_points[0][1], self.zoom_points[1][1]
        
        self._update_data([x1,x2],[y1,y2])

        # Set the new zoom range
        self.ax.set_xlim(min(x1, x2), max(x1, x2))
        self.ax.set_ylim(max(y1, y2), min(y1, y2))
        self.fig.canvas.draw()

    def undo_zoom(self):
        if self.zoom_history:
            xlim, ylim = self.zoom_history.pop()
            self._update_data(xlim,ylim)
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)
            self.fig.canvas.draw()
         
    def draw(self,scale=None, scale_type=None):
        
        if len(self.ax.images)>0:
            self.ax.images[0].remove()
            
        self.data.viz.waterfall(ax=self.ax, scale=self.waterfall_scale, 
                                scale_type=self.waterfall_scale_type,cmap=None)
        self.im = self.ax.images[0]
        self.im.set_cmap('bwr')
#         self.create_colorbar()

    def create_colorbar(self):
        if hasattr(self, 'cbar'):
            self.cbar.remove()
        self.cbar = self.fig.colorbar(self.im)

    def change_clim(self, event=None):
        change_scale = self.change_scale
        if event is not None:
            if event.key == '=':
                self.im.set_clim(self.im.get_clim()[0] * (1+change_scale), self.im.get_clim()[1] * (1+change_scale))
            if event.key == '-':
                self.im.set_clim(self.im.get_clim()[0] * (1-change_scale), self.im.get_clim()[1] * (1-change_scale))
            if event.key == '+':
                color_range = self.im.get_clim()[1] - self.im.get_clim()[0]
                self.im.set_clim(self.im.get_clim()[0] + color_range*0.1 , self.im.get_clim()[1] + color_range*0.1)
            if event.key == '_':
                color_range = self.im.get_clim()[1] - self.im.get_clim()[0]
                self.im.set_clim(self.im.get_clim()[0] - color_range*0.1 , self.im.get_clim()[1] - color_range*0.1)
            
#         self.create_colorbar()
        self.fig.canvas.draw()

    def show(self):
        plt.show()

