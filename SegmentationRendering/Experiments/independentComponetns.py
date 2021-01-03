
import vtk
import vtk.util
import vtk.util.numpy_support

#
# create an elliposid volume and a blurred version of it
#
ellipsoid = vtk.vtkImageEllipsoidSource()
ellipsoid.SetOutputScalarTypeToUnsignedChar()
ellipsoid.SetOutValue(0)
ellipsoid.SetInValue(255)
ellipsoid.SetWholeExtent(0, 299, 0, 299, 0, 299)
ellipsoid.SetRadius(40, 80, 125)
ellipsoid.SetCenter(150, 150, 150)
ellipsoid.Update()

blur = vtk.vtkImageGaussianSmooth()
blur.SetStandardDeviation(3)
blur.SetInputConnection(ellipsoid.GetOutputPort())

#
# make an rgb volume of the same size and assign
# three bands of red, green, and blue
#
colorImage = vtk.vtkImageData()
colorImage.SetDimensions(300, 300, 300)
colorImage.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)

scalars = colorImage.GetPointData().GetScalars()
colorArray = vtk.util.numpy_support.vtk_to_numpy(scalars).reshape(300, 300, 300, 3)
colorArray[0:99,:,:] = [1, 0, 0]
colorArray[100:199,:,:] = [0, 1, 0]
colorArray[200:299,:,:] = [0, 0, 1]

#
# mask the colors so they are only set where original (non-blurred)
# ellipoid is non-zero so they form a stair-stepped segmentation mask
#
ellipsoidScalars = ellipsoid.GetOutputDataObject(0).GetPointData().GetScalars()
ellipsoidArray = vtk.util.numpy_support.vtk_to_numpy(ellipsoidScalars).reshape(300, 300, 300)
colorArray[:,:,:,0] *= ellipsoidArray
colorArray[:,:,:,1] *= ellipsoidArray
colorArray[:,:,:,2] *= ellipsoidArray

#
# make an rgba vectorImage with the blurred
# ellipsoid as the alpha channel
# and use the blurred ellipsoid as a scalarImage
#
append = vtk.vtkImageAppendComponents()
append.AddInputDataObject(colorImage)
append.AddInputConnection(blur.GetOutputPort())
append.Update()
vectorImage = append.GetOutputDataObject(0)
scalarImage = blur.GetOutputDataObject(0)

#
# use the same opacity transfer for both
#
opacityTransferFunction = vtk.vtkPiecewiseFunction()
opacityTransferFunction.RemoveAllPoints()
opacityTransferFunction.AddPoint(10, 0.0)
opacityTransferFunction.AddPoint(255, .4)

#
# make vector and scalar volumes with shading and no
# gradient opacity
#

# vector volume
vectorVolumeProperty = vtk.vtkVolumeProperty()
vectorVolumeProperty.SetScalarOpacity(opacityTransferFunction)
vectorVolumeProperty.ShadeOn()
vectorVolumeProperty.IndependentComponentsOff()
vectorVolumeProperty.SetInterpolationTypeToLinear()
vectorVolumeProperty.DisableGradientOpacityOn()

vectorVolumeMapper = vtk.vtkFixedPointVolumeRayCastMapper()
vectorVolumeMapper = vtk.vtkSmartVolumeMapper()
vectorVolumeMapper.SetInputData(vectorImage)

vectorVolume = vtk.vtkVolume()
vectorVolume.SetMapper(vectorVolumeMapper)
vectorVolume.SetProperty(vectorVolumeProperty)

# scalar volume
scalarVolumeProperty = vtk.vtkVolumeProperty()
scalarVolumeProperty.SetScalarOpacity(opacityTransferFunction)
scalarVolumeProperty.ShadeOn()
scalarVolumeProperty.SetInterpolationTypeToLinear()
scalarVolumeProperty.DisableGradientOpacityOn()

scalarVolumeMapper = vtk.vtkFixedPointVolumeRayCastMapper()
scalarVolumeMapper = vtk.vtkSmartVolumeMapper()
scalarVolumeMapper.SetInputData(scalarImage)

scalarVolume = vtk.vtkVolume()
scalarVolume.SetMapper(scalarVolumeMapper)
scalarVolume.SetProperty(scalarVolumeProperty)


#
# offset the volumes to compare shading
#
vectorVolume.SetPosition(50,0,0)
scalarVolume.SetPosition(-50,0,0)


#
# set up the rest of the rendering as usual
# and add lights to illustrate the bug
#
ren1 = vtk.vtkRenderer()
renWin = vtk.vtkRenderWindow()
renWin.AddRenderer(ren1)
iren = vtk.vtkRenderWindowInteractor()
iren.SetRenderWindow(renWin)

ren1.AddVolume(vectorVolume)
ren1.AddVolume(scalarVolume)

colors = vtk.vtkNamedColors()
ren1.SetBackground(colors.GetColor3d("Gray"))
ren1.GetActiveCamera().Azimuth(45)
ren1.GetActiveCamera().Elevation(30)
ren1.ResetCameraClippingRange()
ren1.ResetCamera()

lights = ren1.GetLights()
light = vtk.vtkLight()
light.SetAmbientColor(0.1, 0.1, 0.1)
light.SetDiffuseColor(0.5, 0.5, 0.5)
light.SetSpecularColor(1.0,1.0,1.0)
light.SetPosition(300.0, 300.0, 300.0)
light.SetIntensity(30.0)
light.SetLightTypeToHeadlight()
lights.AddItem(light)

renWin.SetSize(600, 600)
renWin.Render()

#
# code can be either copy-pasted into Slicer console
# or run in python3 with vtk pip installed
try:
    slicer
except NameError:
    iren.Start()

