
"""
p = "/Users/pieper/slicer/latest/SlicerMorph/SlicerMorph/Experiments/independentComponents.py"
exec(open(p).read())

"""

ellipsoid = vtk.vtkImageEllipsoidSource()
ellipsoid.SetOutputScalarTypeToUnsignedChar()
ellipsoid.SetOutValue(0)
ellipsoid.SetInValue(255)
ellipsoid.SetWholeExtent(0, 299, 0, 299, 0, 299)
ellipsoid.SetRadius(40, 80, 125)
ellipsoid.SetCenter(150, 150, 150)
ellipsoid.Update()

blur = vtk.vtkImageGaussianSmooth()
blur.SetStandardDeviation(.5)
blur.SetInputConnection(ellipsoid.GetOutputPort())

colorImage = vtk.vtkImageData()
colorImage.SetDimensions(300, 300, 300)
colorImage.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)

scalars = colorImage.GetPointData().GetScalars()
colorArray = vtk.util.numpy_support.vtk_to_numpy(scalars).reshape(300, 300, 300, 3)
colorArray[0:99,:,:] = [1, 0, 0]
colorArray[100:199,:,:] = [0, 1, 0]
colorArray[200:299,:,:] = [0, 0, 1]

ellipsoidScalars = ellipsoid.GetOutputDataObject(0).GetPointData().GetScalars()
ellipsoidArray = vtk.util.numpy_support.vtk_to_numpy(ellipsoidScalars).reshape(300, 300, 300)
colorArray[:,:,:,0] *= ellipsoidArray
colorArray[:,:,:,1] *= ellipsoidArray
colorArray[:,:,:,2] *= ellipsoidArray

append = vtk.vtkImageAppendComponents()
append.AddInputDataObject(colorImage)
append.AddInputConnection(blur.GetOutputPort())

append.Update()
vectorImage = append.GetOutputDataObject(0)


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
opacityTransferFunction.AddPoint(0, 0.0)
opacityTransferFunction.AddPoint(255, .1)

# The property describes how the data will look.
volumeProperty = vtk.vtkVolumeProperty()
volumeProperty.SetScalarOpacity(opacityTransferFunction)
volumeProperty.ShadeOn()
volumeProperty.IndependentComponentsOff()
volumeProperty.SetInterpolationTypeToLinear()
volumeProperty.DisableGradientOpacityOn()

# The mapper / ray cast function know how to render the data.
volumeMapper = vtk.vtkFixedPointVolumeRayCastMapper()
volumeMapper = vtk.vtkSmartVolumeMapper()
volumeMapper.SetInputData(vectorImage)

# The volume holds the mapper and the property and
# can be used to position/orient the volume.
volume = vtk.vtkVolume()
volume.SetMapper(volumeMapper)
volume.SetProperty(volumeProperty)

ren1.AddVolume(volume)
colors = vtk.vtkNamedColors()
ren1.SetBackground(colors.GetColor3d("White"))
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
# positional light is not supported by vtkFixedPointVolumeRayCastMapper
light.SetLightTypeToHeadlight()
lights.AddItem(light)

renWin.SetSize(600, 600)
renWin.Render()

