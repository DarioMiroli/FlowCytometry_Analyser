import pyqtgraph as pg
import pyqtgraph.exporters
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
from pyqtgraph.ptime import time as ptime
from scipy import stats
from scipy import interpolate
from scipy.optimize import curve_fit
import numpy as np
import time
import math
import datetime
import os
from functools import partial
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.patches as patches
import FlowCytometryTools
from FlowCytometryTools import FCMeasurement as FCM
from FlowCytometryTools import ThresholdGate, PolyGate, IntervalGate
from scipy.stats import gaussian_kde
from numpy.random import randint
from scipy.optimize import curve_fit
from functools import partial



import matplotlib
matplotlib.rcParams["savefig.directory"] = "./Graphs"

class FlowCytometryAnalyser(QtGui.QWidget):
    '''
    Main application window. Handles live plotting and allows access to data viewer
    and callibration UIs.
    '''

    def __init__(self,parent=None):
        '''
        Constructor for the entire graphing application.
        '''
        self.app = QtGui.QApplication([])
        QtGui.QWidget.__init__(self,parent)
        self.dataDic = {"FileNames":[],"Data":[],"SampleIndexes":[]}
        self.UIDic = {"FileSelectors":[],"XAxisSelectors":[],"YAxisSelectors":[],"LogXAxis":[],
                        "LogYAxis":[],"Plots":[],"PlotLegends":[],"GateCheckBoxes":[],"GateTypeSelector":[],"ROIs":[],
                        "PlotData":[],"SaveBtns":[],"AverageBtns":[],"AverageReigons":[],"AverageReigonCurves":[], "AverageReigonFits":[],
                            "AverageReigonLegendItems":[], "PlotGroupBoxes":[],"AddPlotButtons":[],"PlotLegendItems":[],"NormaliseBtns":[],"AverageReigonValues":[]}
        self.lastPath = None
        self.plotWidgets = []
        self.saveBtns = []
        self.plotGroupBoxes = []
        self.addPlotButtons = []
        self.maxPoints = 10000
        self.setUpUIWidgets()
        self.setUpPlotWidget()
        self.setUpMainWidget()
        self.show()

    def run(self):
        '''
        Starts the main application window. Is blocking.
        '''
        self.app.exec_()

    def setUpPlotWidget(self):
        '''
        Creates plots for linear and log data
        '''
        #Set default background and foreground colors for plots
        pg.setConfigOption('background', (40,40,40))
        pg.setConfigOption('foreground', (220,220,220))
        # Generate grid of plots
        self.plotLayout = QtGui.QGridLayout()

        #self.UIDic["Plots"].append(pg.PlotWidget())
        #self.UIDic["Plots"][0].addLegend()
        #self.UIDic["Plots"]Legends.append(self.UIDic["Plots"][0].plotItem.legend)
        #self.UIDic["Plots"][0].showGrid(x=True,y=True)
        #self.plotLayout.addWidget(self.UIDic["Plots"][0],0,0)

    def setUpUIWidgets(self):
        '''
        Creates all not grpahing UI elements and adds them to the applicatiom
        '''
        self.UILayout = QtGui.QVBoxLayout()

        #File selection for output button and label to display output path
        self.selectFileBtn = QtGui.QPushButton("Load manual data")
        self.selectFileBtn.setToolTip("Choose the file to load.")
        self.selectFileBtn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogOpenButton))
        self.selectFileBtn.setIconSize(QtCore.QSize(24,24))
        self.UILayout.addWidget(self.selectFileBtn)
        self.selectFileBtn.clicked.connect(self.onLoadFilePress)

        #File selection for output button and label to display output path
        self.addPlotBtn = QtGui.QPushButton("Add plot")
        self.addPlotBtn.setToolTip("Add a plot to the grid.")
        self.addPlotBtn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogOpenButton))
        self.addPlotBtn.setIconSize(QtCore.QSize(24,24))
        self.UILayout.addWidget(self.addPlotBtn)
        self.addPlotBtn.clicked.connect(self.onAddPlotPress)

    def setUpMainWidget(self):
        '''
        Combines the UI widgets and the plot widgets to build the final application.
        '''

        self.setWindowTitle('Growth rate plotter')

        #Define relative layout of plotting area and UI widgets
        self.resize(1000,500)
        mainLayout = QtGui.QGridLayout()
        mainLayout.setColumnStretch(0,1)
        #mainLayout.setColumnStretch(1,4)
        #mainLayout.setRowStretch(2,5)

        mainLayout.addLayout(self.plotLayout,0,1)

        # Adds all UI widgets to a vertical scroll area.
        self.scrollWidget = QtGui.QWidget()
        self.UILayout.setSpacing(0)
        self.UILayout.addStretch(0)
        self.scrollWidget.setLayout(self.UILayout)
        self.scroll = QtGui.QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll.setWidget(self.scrollWidget)
        self.scroll.setSizePolicy(QtGui.QSizePolicy.Fixed,QtGui.QSizePolicy.Expanding)
        #scroll.setMaximumSize(self.UILayout.geometry().width()*1.3,2000)
        #scroll.setMinimumSize(self.UILayout.geometry().width()*1.3,200)
        self.scroll.setWidgetResizable(True)
        vLayout = QtGui.QVBoxLayout()
        vLayout.addWidget(self.scroll)
        mainLayout.addLayout(vLayout,0,0)
        self.setLayout(mainLayout)

    def onLoadFilePress(self):
        '''
        Opens the chosen file and plots data
        '''
        if self.lastPath == None:
            openPath = "./"
        else:
            openPath = self.lastPath
        filePath, filter = QtGui.QFileDialog.getOpenFileName(self,
                'Open File', openPath,filter="*.fcs")
        if filePath != "":
            self.loadFile(filePath)
            self.lastPath = filePath

    def loadFile(self,path):
        sample = FCM(ID='Test Sample', datafile=path)
        self.dataDic["FileNames"].append(os.path.basename(path))
        self.dataDic["Data"].append(sample)
        n = (len(sample[sample.channel_names[0]].values))
        if n > self.maxPoints:
            indexes = randint(0,n-1,self.maxPoints)
        else:
            indexes = [i for i in range(n)]
        self.dataDic["SampleIndexes"].append(indexes)
        self.onFileAdded()

    def onAddPlotPress(self):
        self.addPlot()

    def addPlot(self):
        plotBox = QtGui.QGroupBox("Plot {}".format(len(self.plotWidgets)+1))
        plotBoxLayout = QtGui.QGridLayout()
        plotBox.setLayout(plotBoxLayout)

        #Add save file button
        savePlotsButton = QtGui.QPushButton("Save plots")
        savePlotsButton.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogOpenButton))
        savePlotsButton.setIconSize(QtCore.QSize(24,24))
        savePlotsButton.clicked.connect(self.onSavePlot)
        self.saveBtns.append(savePlotsButton)
        plotBoxLayout.addWidget(savePlotsButton,7,1,1,1)

        #Add add subplot button
        addSubPlotBtn = QtGui.QPushButton("Add subplots")
        addSubPlotBtn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogOpenButton))
        addSubPlotBtn.setIconSize(QtCore.QSize(24,24))
        addSubPlotBtn.clicked.connect(partial(self.onAddSubPlot, len(self.plotWidgets)))
        plotBoxLayout.addWidget(addSubPlotBtn,7,2,1,1)
        self.addPlotButtons.append(addSubPlotBtn)

        #Add plot
        self.plotWidgets.append(pg.PlotWidget(padding=0))
        self.plotWidgets[-1].addLegend()
        self.plotWidgets[-1].showGrid(x=True,y=True)
        x,y = self.plotNoToGridCoords(len(self.plotWidgets))
        self.plotLayout.addWidget(self.plotWidgets[-1],y,x)
        #Add group box to UI
        self.UILayout.insertWidget(len(set(self.plotWidgets)),plotBox)
        self.plotGroupBoxes.append(plotBoxLayout)

        #Resize plot
        width = max(self.UILayout.sizeHint().width(),plotBoxLayout.sizeHint().width()+2.0*self.UILayout.contentsMargins().left())
        self.scroll.setMinimumWidth(width + self.scroll.verticalScrollBar().sizeHint().width())

    def addSubPlotUI(self,n):
        fileBox = QtGui.QGroupBox("File {}".format(n))
        fileBoxLayout = QtGui.QGridLayout()
        fileBox.setLayout(fileBoxLayout)

        #Add file combo box
        fileBoxLayout.addWidget(QtGui.QLabel("File"),0,0,1,2)
        fileSelector = QtGui.QComboBox()
        fileSelector.addItems(self.dataDic["FileNames"])
        fileBoxLayout.addWidget(fileSelector,1,0,1,2)
        fileSelector.currentIndexChanged.connect(self.onFileChanged)
        self.UIDic["FileSelectors"].append(fileSelector)

        #Get file name
        fileNameIndex = self.dataDic["FileNames"].index(str(fileSelector.currentText()))
        #Add xaxis selector
        fileBoxLayout.addWidget(QtGui.QLabel("X axis"),2,0,1,2)
        xAxisSelector = QtGui.QComboBox()
        xAxisSelector.addItems(self.dataDic["Data"][fileNameIndex].channel_names)
        xAxisSelector.currentIndexChanged.connect(self.onAxisChange)
        fileBoxLayout.addWidget(xAxisSelector,3,0)
        self.UIDic["XAxisSelectors"].append(xAxisSelector)

        #Add checkbox for logging x axis
        logXAxis = QtGui.QCheckBox("Log x axis")
        fileBoxLayout.addWidget(logXAxis,2,1)
        logXAxis.clicked.connect(self.onLogChange)
        self.UIDic["LogXAxis"].append(logXAxis)

        #Add yaxis selector
        fileBoxLayout.addWidget(QtGui.QLabel("Y axis"),4,0,1,2)
        yAxisSelector = QtGui.QComboBox()
        yAxisSelector.addItems(self.dataDic["Data"][fileNameIndex].channel_names+("Events",))
        yAxisSelector.currentIndexChanged.connect(self.onAxisChange)
        fileBoxLayout.addWidget(yAxisSelector,5,0)
        self.UIDic["YAxisSelectors"].append(yAxisSelector)

        #Add checkbox for logging y axis
        logYAxis = QtGui.QCheckBox("Log y axis")
        fileBoxLayout.addWidget(logYAxis,4,1)
        logYAxis.clicked.connect(self.onLogChange)
        self.UIDic["LogYAxis"].append(logYAxis)

        #Add gate checkbox
        gateCheckBox = QtGui.QCheckBox("Gate on this channel")
        gateCheckBox.clicked.connect(self.onGate)
        self.UIDic["GateCheckBoxes"].append(gateCheckBox)
        fileBoxLayout.addWidget(gateCheckBox,6,0,1,1)

        #Add ROI type selector
        roiSelector = QtGui.QComboBox()
        roiSelector.addItem("square")
        self.UIDic["GateTypeSelector"].append(roiSelector)
        fileBoxLayout.addWidget(roiSelector,6,1,1,1)

        #Add add average reigon button
        addAverageButton = QtGui.QPushButton("Add average")
        addAverageButton.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogOpenButton))
        addAverageButton.setIconSize(QtCore.QSize(24,24))
        addAverageButton.clicked.connect(self.onAddAverage)
        self.UIDic["AverageBtns"].append(addAverageButton)
        fileBoxLayout.addWidget(addAverageButton,7,0,1,1)

        #Add normalise hist button
        normaliseHistBtn = QtGui.QCheckBox("Normalise hists")
        normaliseHistBtn.clicked.connect(self.onNormalise)
        normaliseHistBtn.setChecked(True)
        self.UIDic["NormaliseBtns"].append(normaliseHistBtn)
        fileBoxLayout.addWidget(normaliseHistBtn,7,1,1,1)

        return fileBox

    def onAddSubPlot(self,plotNo):
        self.UIDic["AddPlotButtons"].append(self.addPlotButtons[plotNo])
        index = self.UIDic["AddPlotButtons"].index(self.sender())
        self.UIDic["PlotGroupBoxes"].append(self.plotGroupBoxes[plotNo])
        n = self.UIDic["PlotGroupBoxes"][index].count()
        subPlotWidget = self.addSubPlotUI(n-1)
        self.UIDic["PlotGroupBoxes"][index].addWidget(subPlotWidget,n+1,1,1,2)

        #Add entry to ROI list
        self.UIDic["ROIs"].append(-1)
        self.UIDic["PlotData"].append(-1)
        self.UIDic["Plots"].append(self.plotWidgets[plotNo])
        self.UIDic["SaveBtns"].append(self.saveBtns[plotNo])
        self.UIDic["PlotLegends"].append(self.UIDic["Plots"][-1].plotItem.legend)
        self.UIDic["AverageReigons"].append([])
        self.UIDic["AverageReigonCurves"].append([])
        self.UIDic["AverageReigonFits"].append([])
        self.UIDic["AverageReigonValues"].append([])
        self.UIDic["AverageReigonLegendItems"].append([])
        self.UIDic["PlotLegendItems"].append(pg.PlotDataItem())

        #Add group box to UI
        #self.UILayout.insertWidget(1+len(self.UIDic["Plots"]),plotBox)
        #self.UIDic["PlotGroupBoxes"].append(plotBoxLayout)

        #Resize plot
        width = max(self.UILayout.sizeHint().width(),subPlotWidget.sizeHint().width()+2.0*self.UILayout.contentsMargins().left())
        self.scroll.setMinimumWidth(width + self.scroll.verticalScrollBar().sizeHint().width())

    def plotNoToGridCoords(self,n):
        if n <= 9 :
            coords = [[0,0],[1,0],[0,1],[1,1],[2,0],[2,1],[0,2],[1,2],[2,2]][n-1]
        if n > 9:
            coords = [n%3,math.ceil(n/3.0)-1]
        return coords[0], coords[1]

    def onFileAdded(self):
        for selector in self.UIDic["FileSelectors"]:
            selector.addItems([self.dataDic["FileNames"][-1]])

    def onFileChanged(self):
        index = self.UIDic["FileSelectors"].index(self.sender())
        plot = self.UIDic["Plots"][index]
        xSelect = self.UIDic["XAxisSelectors"][index]
        fileIndex = self.dataDic["FileNames"].index(str(self.sender().currentText()))
        xSelect.clear()


        ySelect = self.UIDic["YAxisSelectors"][index]
        fileIndex = self.dataDic["FileNames"].index(str(self.sender().currentText()))
        ySelect.clear()
        ySelect.addItems(self.dataDic["Data"][fileIndex].channel_names+("Events",))
        xSelect.addItems(self.dataDic["Data"][fileIndex].channel_names)

        self.rePlot(index)

    def rePlot(self,initialUIIndex):
        #Clear plot and replot
        plot = self.UIDic["Plots"][initialUIIndex]
        plot.clear()
        self.clearLegend(initialUIIndex)
        #Get all indexes which need reploted
        UIIndexes = []
        for i in range(len(self.UIDic["Plots"])):
            if self.UIDic["Plots"][i] == plot:
                UIIndexes.append(i)
        nPlots = len(UIIndexes)
        for c,UIIndex in enumerate(UIIndexes):
            fileIndex = self.dataDic["FileNames"].index(str(self.UIDic["FileSelectors"][UIIndex].currentText()))
            fileName =  self.UIDic["FileSelectors"][UIIndex].currentText()
            xSelect = self.UIDic["XAxisSelectors"][UIIndex]
            ySelect = self.UIDic["YAxisSelectors"][UIIndex]

            #Check if we are gating and if yes gate
            gating = False
            for checkBox in self.UIDic["GateCheckBoxes"]:
                if checkBox.isChecked():
                    gateIndex = self.UIDic["GateCheckBoxes"].index(checkBox)
                    gateFileName =   self.UIDic["FileSelectors"][gateIndex].currentText()
                    if gateFileName == fileName:
                        gating = True
                        break

                    #break
            if gating:
                #Get coords of
                data = self.dataDic["Data"][fileIndex]
                roi = self.UIDic["ROIs"][gateIndex]
                gateBounds = roi.parentBounds()
                x1 = gateBounds.bottomLeft().x()
                x2 = gateBounds.bottomRight().x()
                y1 = gateBounds.topLeft().y()
                y2 = gateBounds.bottomRight().y()
                xChannel = str(self.UIDic["XAxisSelectors"][gateIndex].currentText())
                yChannel = str(self.UIDic["YAxisSelectors"][gateIndex].currentText())
                gate = PolyGate([(x1,y1),(x2,y1),(x2,y2),(x1,y2)],channels = [xChannel,yChannel])
                data = data.gate(gate)
            else:
                data = self.dataDic["Data"][fileIndex]


            if str(ySelect.currentText()) == "Events":
                z = data[str(xSelect.currentText())]
                color = pg.mkColor((UIIndex,nPlots))
                color.setAlpha(int(100))
                if len(z) > 0:
                    y,x = np.histogram(z, bins=np.linspace(min(z), max(z), 1000))
                    if self.UIDic["NormaliseBtns"][UIIndex].isChecked():
                        y = y/len(z)
                    curve = pg.PlotCurveItem(x, y, stepMode=True, fillLevel=0, brush=color,pen=color)
                    self.removeLegendItem(self.UIDic["PlotLegends"][UIIndex],self.UIDic["PlotLegendItems"][UIIndex])
                    self.UIDic["PlotLegendItems"][UIIndex] = curve
                    self.UIDic["PlotLegends"][UIIndex].addItem(curve,"{0} N={1} ".format(fileName,len(z)))
                    for reigon in self.UIDic["AverageReigons"][UIIndex]:
                        pass
                else:
                    curve = pg.PlotCurveItem([], [])

            else:
                curve = pg.ScatterPlotItem(pen=None,brush=(c,nPlots),pxMode=True,size=2)
                x = data[str(xSelect.currentText())]
                y = data[str(ySelect.currentText())]
                self.removeLegendItem(self.UIDic["PlotLegends"][UIIndex],self.UIDic["PlotLegendItems"][UIIndex])
                self.UIDic["PlotLegendItems"][UIIndex] = curve
                self.UIDic["PlotLegends"][UIIndex].addItem(curve,"{0} N={1} ".format(fileName,len(x)))
                if gating:
                    if len(x) > self.maxPoints:
                        indexes = randint(0,len(x),self.maxPoints)
                    else:
                        indexes = [i for i in range(len(x))]
                else:
                    indexes = self.dataDic["SampleIndexes"][fileIndex]
                x = np.asarray(x)[indexes]
                y = np.asarray(y)[indexes]
                if self.UIDic["LogXAxis"][UIIndex].isChecked():
                    #x = np.sign(x)* np.log10(abs(x) + 1)
                    x = np.log(x + abs(min(x)) + 1)
                if self.UIDic["LogYAxis"][UIIndex].isChecked():
                    #y = np.sign(y)* np.log10(abs(y) + 1)
                    y = np.log(y + abs(min(y)) + 1)
                curve.setData(x,y)
            self.UIDic["PlotData"][UIIndex] = data
            self.UIDic["Plots"][UIIndex].addItem(curve)
            #Add axis labels
            self.UIDic["Plots"][UIIndex].setLabel('left', str(self.UIDic["YAxisSelectors"][UIIndex].currentText()))
            self.UIDic["Plots"][UIIndex].setLabel('bottom', str(self.UIDic["XAxisSelectors"][UIIndex].currentText()))

            #Add reigons we cleared
            if str(ySelect.currentText()) == "Events":
                for reigon in self.UIDic["AverageReigons"][UIIndex]:
                    self.UIDic["Plots"][UIIndex].addItem(reigon)

    def onAxisChange(self):
        try:
            uiIndex = self.UIDic["XAxisSelectors"].index(self.sender())
        except:
            uiIndex = self.UIDic["YAxisSelectors"].index(self.sender())
        if  str(self.UIDic["XAxisSelectors"][uiIndex].currentText()) != '' and str(self.UIDic["YAxisSelectors"][uiIndex].currentText()) != '':
            self.clearAveragereigons(uiIndex)
            fileIndex = self.dataDic["FileNames"].index(str(self.UIDic["FileSelectors"][uiIndex].currentText()))
            if self.UIDic["GateCheckBoxes"][uiIndex].isChecked():
                self.UIDic["GateCheckBoxes"][uiIndex].animateClick()
            else:
                self.rePlot(uiIndex)

    def onLogChange(self):
        checkBox = self.sender()
        try:
            uiIndex = self.UIDic["LogXAxis"].index(checkBox)
        except:
            uiIndex = self.UIDic["LogYAxis"].index(checkBox)
        fileName = str(self.UIDic["FileSelectors"][uiIndex].currentText())
        fileIndex = self.dataDic["FileNames"].index(fileName)
        self.rePlot(uiIndex)

    def onGate(self):
        on = self.sender().isChecked()
        UIIndex = self.UIDic["GateCheckBoxes"].index(self.sender())
        gateName =  self.UIDic["FileSelectors"][UIIndex].currentText()
        plot = self.UIDic["Plots"][UIIndex]
        #Check if ROI holds -1 and thus is first time this ROI has been interacted with
        if self.UIDic["ROIs"][UIIndex] == -1:
            self.UIDic["ROIs"][UIIndex] = pg.RectROI([1,1],[1,1], pen=(0,9),centered=False)

        #Turn off all check boxes remove ROIS
        for i,checkBox in enumerate(self.UIDic["GateCheckBoxes"]):
            fileName =  self.UIDic["FileSelectors"][i].currentText()
            if fileName == gateName:
                checkBox.setChecked(False)
                try:
                    self.UIDic["Plots"][i].removeItem(self.UIDic["ROIs"][i])
                except:
                    pass

        #Then replot each graph
        for i in range(len(self.UIDic["Plots"])):
            fIndex = self.dataDic["FileNames"].index(str(self.UIDic["FileSelectors"][i].currentText()))
            if self.UIDic["Plots"][i] != plot:
                self.rePlot(i)

        #If we meant to turn a gate on
        if on:
            self.sender().setChecked(True)
            plot = self.UIDic["Plots"][UIIndex]
            plotData = self.UIDic["PlotData"][UIIndex]
            #ROIS?
            xData = plotData[str(self.UIDic["XAxisSelectors"][UIIndex].currentText())]
            yData = plotData[str(self.UIDic["YAxisSelectors"][UIIndex].currentText())]
            minX = min(xData)
            maxX = max(xData)
            minY = min(yData)
            maxY = max(yData)
            ix = minX
            iy = minY
            xSpan = abs(maxX-minX)
            ySpan = abs(maxY-minY)
            bounds = QtCore.QRectF(ix,iy,xSpan,ySpan)
            self.UIDic["ROIs"][UIIndex] = pg.RectROI([ix,iy], [xSpan,ySpan], pen=(0,9),centered=False,maxBounds=bounds)
            self.UIDic["ROIs"][UIIndex].addScaleHandle((0,0),(1,1))
            self.UIDic["ROIs"][UIIndex].addScaleHandle((0,1),(1,0))
            self.UIDic["ROIs"][UIIndex].addScaleHandle((1,0),(0,1))
            self.UIDic["ROIs"][UIIndex].addScaleHandle((0,0.5),(1,0.5))
            self.UIDic["ROIs"][UIIndex].addScaleHandle((0.5,0),(0.5,1))
            self.UIDic["ROIs"][UIIndex].addScaleHandle((1,0.5),(0,0.5))
            self.UIDic["ROIs"][UIIndex].addScaleHandle((0.5,1),(0.5,0))
            self.UIDic["ROIs"][UIIndex].sigRegionChangeFinished.connect(self.onROIMove)
            plot.addItem(self.UIDic["ROIs"][UIIndex])
            self.recolorROIs()
            self.onROIMove()

    def onROIMove(self):
        noReplotPlots = []
        for i,checkBox in enumerate(self.UIDic["GateCheckBoxes"]):
            if checkBox.isChecked():
                noReplotPlots.append(self.UIDic["Plots"][i])

        for i,plot in enumerate(self.UIDic["Plots"]):
            if not plot in noReplotPlots:
                self.rePlot(i)

    def onSavePlot(self):
        i = self.UIDic["SaveBtns"].index(self.sender())
        self.savePlot("",i)

    def savePlot(self,fileName,UIIndex):
        SaveWindow(UIIndex,self.dataDic,self.UIDic)

    def onAddAverage(self):
        uiIndex = self.UIDic["AverageBtns"].index(self.sender())
        plot = self.UIDic["Plots"][uiIndex]
        #Get x values
        plotData = self.UIDic["PlotData"][uiIndex]
        #ROIS?
        xData = plotData[str(self.UIDic["XAxisSelectors"][uiIndex].currentText())]
        minX = min(xData)
        maxX = max(xData)
        hReigon = pg.LinearRegionItem([minX,0.1*maxX],movable=True,bounds=[minX,maxX])
        hReigon.sigRegionChangeFinished.connect(self.onAverageMove)
        plot.addItem(hReigon)
        self.UIDic["AverageReigons"][uiIndex].append(hReigon)
        self.UIDic["AverageReigonCurves"][uiIndex].append(pg.PlotCurveItem())
        self.UIDic["AverageReigonFits"][uiIndex].append("")
        self.UIDic["AverageReigonValues"][uiIndex].append("")
        self.UIDic["AverageReigonLegendItems"][uiIndex].append(pg.PlotCurveItem())

    def onAverageMove(self):
        #Get correct plot
        uiIndex = None
        for i in range(len(self.UIDic["AverageReigons"])):
            if self.sender() in self.UIDic["AverageReigons"][i]:
                uiIndex = i
        plot = self.UIDic["Plots"][uiIndex]
        UIIndexes = []
        for i in range(len(self.UIDic["Plots"])):
            if self.UIDic["Plots"][i] == plot:
                UIIndexes.append(i)
        #self.UIDic["PlotLegends"][uiIndex].items = []
        #self.clearLegend(uiIndex)
        for uiIndex in UIIndexes:

            if uiIndex != None:
                plot = self.UIDic["Plots"][uiIndex]
                data = self.UIDic["PlotData"][uiIndex]
                for c,reigon in enumerate(self.UIDic["AverageReigons"][uiIndex]):
                    color = pg.mkColor((c,len(self.UIDic["AverageReigons"][uiIndex])))
                    color.setAlpha(int(25))
                    reigon.setBrush(color)
                    xmin,xmax = reigon.getRegion()
                    gate = IntervalGate((xmin,xmax),channel=str(self.UIDic["XAxisSelectors"][uiIndex].currentText()),region='in')
                    gated = data.gate(gate)
                    mean = gated[str(self.UIDic["XAxisSelectors"][uiIndex].currentText())].mean()
                    color.setAlpha(int(255))
                    x1,x2 = reigon.getRegion()
                    z = gated[self.UIDic["XAxisSelectors"][uiIndex].currentText()]
                    y,x = np.histogram(z, bins=np.linspace(min(z), max(z), 1000*((x2-x1)/max(data[self.UIDic["XAxisSelectors"][uiIndex].currentText()]))))
                    x = [x[i] + (x[i+1]-x[i])/2.0 for i in range(len(x)-1)]
                    xfit,yfit, popts = self.getHistogramFit(x,y,x1,x2)
                    if self.UIDic["NormaliseBtns"][uiIndex].isChecked():
                        yfit = yfit/len(data[str(self.UIDic["XAxisSelectors"][uiIndex].currentText())])
                    self.removeLegendItem(self.UIDic["PlotLegends"][uiIndex], self.UIDic["AverageReigonLegendItems"][uiIndex][c])
                    legendItem = pg.PlotDataItem(pen=color)
                    self.UIDic["AverageReigonLegendItems"][uiIndex][c] = legendItem
                    populationPercent = 100*len(gated[str(self.UIDic["XAxisSelectors"][uiIndex].currentText())])/len(data[str(self.UIDic["XAxisSelectors"][uiIndex].currentText())])
                    self.UIDic["PlotLegends"][uiIndex].addItem(legendItem,"{0} +- {1} %{2}".format(round(popts[1],1),round(popts[2],1),round(populationPercent,0)))
                    curve = pg.PlotCurveItem(xfit, yfit,pen=(0,0,0))
                    self.UIDic["Plots"][uiIndex].removeItem(self.UIDic["AverageReigonCurves"][uiIndex][c])
                    self.UIDic["AverageReigonCurves"][uiIndex][c] = curve
                    self.UIDic["AverageReigonFits"][uiIndex][c] = "mean: {0} Sdev: {1} %: {2}".format(round(popts[1],1),round(popts[2],1),round(populationPercent,1))
                    self.UIDic["AverageReigonValues"][uiIndex][c] = round(popts[1],1)
                    self.UIDic["Plots"][uiIndex].addItem(curve)

    def getHistogramFit(self,x,y,x1,x2):
        def gaussian(x,a,b,c):
            y = a * np.exp((-1.0*(x-b)**2)/(2*(c**2)))
            return y
        guessA = max(y)
        guessB = (x1+x2)/2
        guessC = x2-x1
        try:
            popt,pcov = curve_fit(gaussian,x,y,p0=[guessA,guessB,guessC])
        except:
            popt = (guessA,guessB,guessC)
        xfit = np.linspace(x1,x2,100)
        yfit = gaussian(xfit,*popt)
        return xfit, yfit, popt

    def clearLegend(self,uiIndex):
        #self.UIDic["PlotLegends"][uiIndex].scene().removeItem(self.UIDic["PlotLegends"][uiIndex])
        #self.UIDic["Plots"][uiIndex].addLegend()
        #for i in range(len(self.UIDic["PlotLegends"])):
        #    if self.UIDic["Plots"][i] == self.UIDic["Plots"][uiIndex]:
        #        self.UIDic["PlotLegends"][i] = self.UIDic["Plots"][uiIndex].plotItem.legend
        legend = self.UIDic["PlotLegends"][uiIndex]
        items =  self.UIDic["AverageReigonLegendItems"][uiIndex]
        for item in items:
            self.removeLegendItem(legend,item)

    def removeLegendItem(self,legend,delitem):
        for i,item in enumerate(legend.items):
            if item[0].item == delitem:
                del legend.items[i]

    def clearAveragereigons(self,uiIndex):
        for i in range(len(self.UIDic["AverageReigons"])):
            self.UIDic["Plots"][uiIndex].removeItem(self.UIDic["AverageReigons"][i])
        self.UIDic["AverageReigons"][uiIndex] = []
        self.UIDic["AverageReigonCurves"][uiIndex] = []

    def recolorROIs(self):
        for plot in self.UIDic["Plots"]:
            UIIndexes = []
            for i in range(len(self.UIDic["Plots"])):
                if self.UIDic["Plots"][i] == plot:
                    UIIndexes.append(i)
            nPlots = len(UIIndexes)
            for c,index in enumerate(UIIndexes):
                if self.UIDic["GateCheckBoxes"][index].isChecked():
                    self.UIDic["ROIs"][index].setPen((c,nPlots))

    def onNormalise(self):
        btn = self.sender()
        uiIndex = self.UIDic["NormaliseBtns"].index(btn)
        self.rePlot(uiIndex)

class SaveWindow(QtGui.QMainWindow):

    def __init__(self,uiIndex,dataDic,UIDic,parent=None):
        QtGui.QMainWindow.__init__(self,parent)
        self.dataDic = dataDic
        self.UIDic = UIDic
        self.uiIndex = uiIndex
        self.setWindowTitle("Saveplot")
        self.setUpUI()
        self.setUpPlots()
        self.setUpMainWidget()
        self.plotData()

    def setUpUI(self):
        self.uiLayout = QtGui.QGridLayout()
        #if str(self.UIDic["YAxisSelectors"][self.uiIndex].currentText()) != "Events":
        self.scatterButton = QtGui.QRadioButton("Scatter")
        self.scatterButton.setChecked(True)
        self.hexBinButton = QtGui.QRadioButton("Hexbins")
        self.scatterButton.clicked.connect(self.plotData)
        self.hexBinButton.clicked.connect(self.plotData)

        self.normaliseBtn = QtGui.QCheckBox("Normalise")
        self.normaliseBtn.clicked.connect(self.plotData)

        self.rescaleBtn = QtGui.QCheckBox("Rescale")
        self.rescaleBtn.clicked.connect(self.plotData)

        self.rescaleInputBoxes = []
        for i in range(len(self.dataDic["FileNames"])):
            rescaleInput = QtGui.QDoubleSpinBox()
            rescaleInput.setMinimum(0)
            rescaleInput.setMaximum(1e100)
            rescaleInput.setValue(1)
            rescaleInput.valueChanged.connect(self.plotData)
            self.rescaleInputBoxes.append(rescaleInput)

        self.format256Btn = QtGui.QCheckBox("256 format")
        self.format256Btn.clicked.connect(self.plotData)

        self.saveTextBtn = QtGui.QPushButton("Save text file")
        self.saveTextBtn.clicked.connect(self.onSavePress)

        self.uiLayout.addWidget(self.scatterButton,0,0,1,1)
        self.uiLayout.addWidget(self.hexBinButton,1 ,0,1,1)
        self.uiLayout.addWidget(self.normaliseBtn,2 ,0,1,1)
        self.uiLayout.addWidget(self.rescaleBtn,3,0,1,1)
        for i,box in enumerate(self.rescaleInputBoxes):
            self.uiLayout.addWidget(box,4+i,0,1,1)
        self.uiLayout.addWidget(self.format256Btn,5+len(self.rescaleInputBoxes),0,1,1)
        self.uiLayout.addWidget(self.saveTextBtn,6+len(self.rescaleInputBoxes),0,1,1)

    def setUpPlots(self):
        # a figure instance to plot on
        self.figure = Figure()
        # this is the Canvas Widget that displays the `figure`
        # it takes the `figure` instance as a parameter to __init__
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        # this is the Navigation widget
        # it takes the Canvas widget and a parent
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.plotLayout = QtGui.QGridLayout()
        self.plotLayout.addWidget(self.canvas,0,0)
        self.plotLayout.addWidget(self.toolbar,1,0)

    def setUpMainWidget(self):
        self.mainWidget = QtGui.QWidget()
        self.mainLayout = QtGui.QGridLayout()
        self.mainLayout.addLayout(self.uiLayout,0,0)
        self.mainLayout.addLayout(self.plotLayout,0,1)
        self.mainWidget.setLayout(self.mainLayout)
        self.setCentralWidget(self.mainWidget)
        self.show()

    def plotData(self):
        plot = self.UIDic["Plots"][self.uiIndex]
        UIIndexes = []
        for i in range(len(self.UIDic["Plots"])):
            if self.UIDic["Plots"][i] == plot:
                UIIndexes.append(i)
        nPlots = len(UIIndexes)

        # create an axis
        #ax = self.figure.add_subplot(111)
        ax = self.figure.gca()
        # discards the old graph
        ax.clear()

        xlabels = []
        ylabels = []
        titles = []
        for i in UIIndexes:
            xlabels.append(str(self.UIDic["XAxisSelectors"][i].currentText()))
            ylabels.append(str(self.UIDic["YAxisSelectors"][i].currentText()))
            titles.append(str(self.UIDic["FileSelectors"][i].currentText()))

        xlabel = " / ".join(list(set(xlabels)))
        ylabel =  " / ".join(list(set(ylabels)))
        fileName =   " / ".join(list(set(titles)))


        for i, uiIndex in enumerate(UIIndexes):
            data = self.UIDic["PlotData"][uiIndex]
            xdata = data[str(self.UIDic["XAxisSelectors"][uiIndex].currentText())]
            label = ''
            if len(list(set(titles))) > 1:
                label+= titles[i] + " "
            if len(list(set(xlabels))) > 1 or len(list(set(ylabels))) >1:
                label += xlabels[i] + " vs " + ylabels[i]
            # plot data
            if str(self.UIDic["YAxisSelectors"][uiIndex].currentText()) != "Events":
                ydata = data[str(self.UIDic["YAxisSelectors"][uiIndex].currentText())]
                label += " N= {}".format(len(ydata))
                if self.scatterButton.isChecked():
                     p = ax.plot(xdata.values,ydata.values, '.', markersize = 1,zorder=1,label=label,alpha=0.5)
                     color = p[0].get_color()
                else:
                    ax.hexbin(xdata.values,ydata.values,gridsize=1000,cmap='jet',bins='log',zorder=1,mincnt=2)
                    #h = ax.hist2d(xdata,ydata,1000,norm=mpl.colors.LogNorm(),cmin=2,vmin=1)
                    #plt.colorbar(h[3], ax=ax)
                if self.UIDic["GateCheckBoxes"][uiIndex].isChecked():
                    roi = self.UIDic["ROIs"][uiIndex]
                    gateBounds = roi.parentBounds()
                    x1 = gateBounds.bottomLeft().x()
                    x2 = gateBounds.bottomRight().x()
                    y1 = gateBounds.topLeft().y()
                    y2 = gateBounds.bottomRight().y()
                    rect = patches.Rectangle((x1,y1),x2-x1,y2-y1,linewidth=1,edgecolor=color,facecolor='none',zorder=2,label="gate")
                    ax.add_patch(rect)
            else:
                label += " N= {}".format(len(xdata.values))
                if self.rescaleBtn.isChecked() and not self.format256Btn.isChecked() :
                    xdata = xdata/self.rescaleInputBoxes[i].value()
                    if max(xdata) < 100:
                        ax.xaxis.set_ticks(np.arange(0, round(max(xdata)), 1.0))
                if self.normaliseBtn.isChecked() and not self.format256Btn.isChecked():
                    weights = np.ones_like(xdata.values)/float(len(xdata.values))
                    ax.hist(xdata.values,bins=1000,label=label,zorder=2,alpha=0.5,histtype='step',weights=weights,linewidth=3.0)
                if self.format256Btn.isChecked():
                    xdata =  ( xdata/max(xdata) )*256
                    ax.hist(xdata.values,bins=256,label=label,zorder=2,alpha=0.5,histtype='step',range=(0,256),linewidth=3.0)
                if not self.format256Btn.isChecked() and not self.normaliseBtn.isChecked():
                    ax.hist(xdata.values,bins=1000,label=label,zorder=2,alpha=0.5,histtype='step',linewidth=3.0)

                nCols = len(self.UIDic["AverageReigons"][uiIndex])
                for c,reigon in enumerate(self.UIDic["AverageReigons"][uiIndex]):
                    x1,x2 = reigon.getRegion()
                    color = pg.intColor(c,nCols)
                    r,g,b,a = color.getRgb()
                    #ax.axvspan(x1, x2, alpha=0.2,label=mean,facecolor=(r/255.0,g/255.0,b/255.0))
                for k,curve in enumerate(self.UIDic["AverageReigonCurves"][uiIndex]):
                    xfit,yfit = curve.getData()
                    if self.UIDic["NormaliseBtns"][uiIndex].isChecked():
                        yfit = yfit*(len(xdata.values))
                    if self.normaliseBtn.isChecked():
                        yfit = yfit/(len(xdata.values))
                    if self.rescaleBtn.isChecked():
                        xfit = xfit/self.rescaleInputBoxes[i].value()
                    print(self.UIDic["AverageReigonValues"][uiIndex][k])
                    ax.plot(xfit,yfit,label=float(self.UIDic["AverageReigonValues"][uiIndex][k])/self.rescaleInputBoxes[i].value())
                #if len(self.UIDic["AverageReigonCurves"][uiIndex]) > 0:
                ax.legend()
            if label != '':
                legend = ax.legend()
                for handle in legend.legendHandles:
                    try:
                        handle._legmarker.set_markersize(9)
                    except:
                        pass
            ax.set_xlabel(xlabel,fontsize=20)
            ax.set_ylabel(ylabel,fontsize=20)
            ax.xaxis.set_tick_params(labelsize=15)
            ax.yaxis.set_tick_params(labelsize=15)
            ax.set_title(fileName,fontsize=20)
            # refresh canvas
            self.canvas.draw()

    def onSavePress(self):
        if self.format256Btn.isChecked():
            fileName, filter = QtGui.QFileDialog.getSaveFileName(parent=self,caption='Select file', filter='*.txt')
            if fileName != "":
                data = self.UIDic["PlotData"][self.uiIndex]
                xdata = data[str(self.UIDic["XAxisSelectors"][self.uiIndex].currentText())]
                xdata =  ( xdata/max(xdata) )*256
                n,bins,patches = plt.hist(xdata.values,bins=256,histtype='step',range=(0,256))
                f = open(fileName, "w")
                for i in range(len(n)):
                    f.write("{0}\n".format(n[i]))


if __name__ == '__main__':
    from FlowCytometryApp import FlowCytometryAnalyser

    FCA1 = FlowCytometryAnalyser()
    FCA1.run()
    exit()
