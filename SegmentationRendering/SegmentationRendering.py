import os
import unittest
import logging
import vtk, qt, ctk, slicer, numpy
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

#
# SegmentationRendering
#

class SegmentationRendering(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Segmentation Rendering"
    self.parent.categories = ["Segmentations"]
    self.parent.dependencies = []
    self.parent.contributors = ["Steve Pieper (Isomics, Inc.)"]
    self.parent.helpText = """
This module creates a vector volume where each voxel is a colored by any segment that covers is and the alpha value comes from the referenced volume.
"""
    self.parent.acknowledgementText = """
Funded in part by the NSF Advances in Biological Informatics Collaborative grant to ABI-1759883

This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
"""

#
# SegmentationRenderingWidget
#

class SegmentationRenderingWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/SegmentationRendering.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = SegmentationRenderingLogic()

    # Connections

    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).
    self.ui.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.referenceSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.invertOutputCheckBox.connect("toggled(bool)", self.updateParameterNodeFromGUI)

    # Buttons
    self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)

    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()

  def enter(self):
    """
    Called each time the user opens this module.
    """
    # Make sure parameter node exists and observed
    self.initializeParameterNode()

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

  def onSceneStartClose(self, caller, event):
    """
    Called just before the scene is closed.
    """
    # Parameter node will be reset, do not use it anymore
    self.setParameterNode(None)

  def onSceneEndClose(self, caller, event):
    """
    Called just after the scene is closed.
    """
    # If this module is shown while the scene is closed then recreate a new parameter node immediately
    if self.parent.isEntered:
      self.initializeParameterNode()

  def initializeParameterNode(self):
    """
    Ensure parameter node exists and observed.
    """
    # Parameter node stores all user choices in parameter values, node selections, etc.
    # so that when the scene is saved and reloaded, these settings are restored.

    self.setParameterNode(self.logic.getParameterNode())

    # TODO
    """
    # Select default input nodes if nothing is selected yet to save a few clicks for the user
    if not self._parameterNode.GetNodeReference("InputVolume"):
      firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
      if firstVolumeNode:
        self._parameterNode.SetNodeReferenceID("InputVolume", firstVolumeNode.GetID())
    """

  def setParameterNode(self, inputParameterNode):
    """
    Set and observe parameter node.
    Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
    """

    if inputParameterNode:
      self.logic.setDefaultParameters(inputParameterNode)

    # Unobserve previously selected parameter node and add an observer to the newly selected.
    # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
    # those are reflected immediately in the GUI.
    if self._parameterNode is not None:
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    self._parameterNode = inputParameterNode
    if self._parameterNode is not None:
      self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
    self._updatingGUIFromParameterNode = True

    # TODO
    """
    # Update node selectors and sliders
    self.ui.inputSelector.setCurrentNode(self._parameterNode.GetNodeReference("InputVolume"))
    self.ui.outputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputVolume"))

    # Update buttons states and tooltips
    if self._parameterNode.GetNodeReference("InputVolume") and self._parameterNode.GetNodeReference("OutputVolume"):
      self.ui.applyButton.toolTip = "Compute output volume"
      self.ui.applyButton.enabled = True
    else:
      self.ui.applyButton.toolTip = "Select input and output volume nodes"
      self.ui.applyButton.enabled = False
    """

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    self._parameterNode.SetNodeReferenceID("InputVolume", self.ui.inputSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("OutputVolume", self.ui.outputSelector.currentNodeID)

    self._parameterNode.EndModify(wasModified)

  def onApplyButton(self):
    """
    Run processing when user clicks "Apply" button.
    """
    try:

      # Compute output
      self.logic.process(self.ui.inputSelector.currentNode(), self.ui.outputSelector.currentNode())

    except Exception as e:
      slicer.util.errorDisplay("Failed to compute results: "+str(e))
      import traceback
      traceback.print_exc()


#
# SegmentationRenderingLogic
#

class SegmentationRenderingLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Threshold"):
      parameterNode.SetParameter("Threshold", "100.0")

def makeVectorVolume(segmentationNode, referenceNode, labelmapNode=None, colorNode=None, vectorNode=None):
  """
  Create the vector volume based on the segmentation and reference.
  Can be used without GUI widget.
  :param segmentationNode: to be used
  :param referenceNode: defines vector volume geometry and alpha
  :param labelmapNode: used as an intermediate value, will be create if None
  :param colorNode: used as an intermediate value, will be create if None
  :param vectorNode: result, new will be created if None
  """

  """
p = "/Users/pieper/slicer/latest/SlicerMorph/SlicerMorph/SegmentationRendering/SegmentationRendering.py"
exec(open(p).read())

  """

  if not segmentationNode or not referenceNode:
    raise ValueError("input is invalid")

  import time
  startTime = time.time()
  logging.info('Processing started')

  import vtkSlicerSegmentationsModuleLogicPython as vtkSlicerSegmentationsModuleLogic
  logic = vtkSlicerSegmentationsModuleLogic.vtkSlicerSegmentationsModuleLogic()

  segmentIDs = vtk.vtkStringArray()
  segmentationNode.GetSegmentation().GetSegmentIDs(segmentIDs)

  if not labelmapNode:
    labelmapNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
  if not vectorNode:
    vectorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLVectorVolumeNode")

  referenceImage = referenceNode.GetImageData()
  vectorImage = vtk.vtkImageData()
  vectorImage.SetDimensions(referenceImage.GetDimensions())
  vectorImage.AllocateScalars(referenceImage.GetScalarType(), 4)
  vectorNode.SetAndObserveImageData(vectorImage)
  ijkToRAS = vtk.vtkMatrix4x4()
  referenceNode.GetIJKToRASMatrix(ijkToRAS)
  vectorNode.SetIJKToRASMatrix(ijkToRAS)


  success = logic.ExportSegmentsToLabelmapNode(segmentationNode, segmentIDs, labelmapNode, referenceNode, slicer.vtkSegmentation.EXTENT_REFERENCE_GEOMETRY)

  if not success:
    return None

  referenceArray = slicer.util.array(referenceNode.GetID())
  labelArray = slicer.util.array(labelmapNode.GetID())
  vectorArray = slicer.util.array(vectorNode.GetID())
  vectorArray.fill(0)

  vectorArray[:,:,:,3] = 255 * referenceArray.astype('float32') / referenceArray.max()
  lookupTable = labelmapNode.GetDisplayNode().GetColorNode().GetLookupTable()
  rgb = [0]*3
  labels = numpy.unique(labelArray)
  for label in labels:
    labelMask = numpy.zeros(vectorArray[:,:,:,0:3].shape, dtype=vectorArray.dtype)
    labelMask[numpy.where(labelArray == label)] = 1
    lookupTable.GetColor(label, rgb)
    vectorArray[:,:,:,0:3] += (255 * numpy.asarray(rgb)).astype(vectorArray.dtype) * labelMask

  slicer.util.arrayFromVolumeModified(vectorNode)

  cast = vtk.vtkImageCast()
  cast.SetInputData(vectorNode.GetImageData())
  cast.SetOutputScalarTypeToUnsignedChar()
  cast.Update()
  vectorNode.SetAndObserveImageData(cast.GetOutputDataObject(0))

  colors = vtk.vtkNamedColors()

  # Create the standard renderer, render window
  # and interactor.
  ren1 = vtk.vtkRenderer()

  renWin = vtk.vtkRenderWindow()
  renWin.AddRenderer(ren1)

  iren = vtk.vtkRenderWindowInteractor()
  iren.SetRenderWindow(renWin)
  #iren.GetInteractorStyle().SetCurrentStyleToTrackballActor()

  # Create transfer mapping scalar value to opacity.
  opacityTransferFunction = vtk.vtkPiecewiseFunction()
  opacityTransferFunction.RemoveAllPoints()
  opacityTransferFunction.AddPoint(12.5, 0.0)
  opacityTransferFunction.AddPoint(255, 0.2)

  # The property describes how the data will look.
  volumeProperty = vtk.vtkVolumeProperty()
  volumeProperty.SetScalarOpacity(opacityTransferFunction)
  #volumeProperty.ShadeOn()
  volumeProperty.IndependentComponentsOff()
  volumeProperty.SetInterpolationTypeToLinear()

  # The mapper / ray cast function know how to render the data.
  volumeMapper = vtk.vtkFixedPointVolumeRayCastMapper()
  volumeMapper = vtk.vtkSmartVolumeMapper()
  volumeMapper.SetInputData(vectorImage)

  volumeMapper.SetInputData(vectorNode.GetImageData())

  # The volume holds the mapper and the property and
  # can be used to position/orient the volume.
  volume = vtk.vtkVolume()
  volume.SetMapper(volumeMapper)
  volume.SetProperty(volumeProperty)

  ren1.AddVolume(volume)
  ren1.SetBackground(colors.GetColor3d("Wheat"))
  ren1.GetActiveCamera().Azimuth(45)
  ren1.GetActiveCamera().Elevation(30)
  ren1.ResetCameraClippingRange()
  ren1.ResetCamera()

  renWin.SetSize(600, 600)
  renWin.Render()

  slicer.modules.renWin = renWin


  import vtkTeem
  writer = vtkTeem.vtkTeemNRRDWriter()
  writer.SetFileName("/tmp/VectorVolume.nrrd")
  writer.SetInputData(vectorImage)
  writer.Write()


  stopTime = time.time()
  logging.info('Processing completed in {0:.2f} seconds'.format(stopTime-startTime))

#
# SegmentationRenderingTest
#

class SegmentationRenderingTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_SegmentationRendering1()

  def test_SegmentationRendering1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")

    # Get/create input data

    import SampleData
    inputVolume = SampleData.downloadMRHead()
    self.delayDisplay('Loaded test data set')

    logic = SegmentationRenderingLogic()

    # Test algorithm
    """
    logic.process(inputVolume, outputVolume, threshold)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], threshold)
    """


    self.delayDisplay('Test passed')
