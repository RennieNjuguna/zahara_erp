from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Crop, FarmBlock
from .forms import CropForm, FarmBlockForm


def dashboard(request):
    """Main dashboard for planting schedule"""
    context = {
        'total_crops': Crop.objects.count(),
        'recent_crops': Crop.objects.order_by('-created_at')[:5],
        'total_blocks': FarmBlock.objects.count(),
        'recent_blocks': FarmBlock.objects.order_by('-created_at')[:5],
    }
    return render(request, 'planting_schedule/dashboard.html', context)


# Crop Views
def crop_list(request):
    """List all crops"""
    crops = Crop.objects.all().order_by('name')
    context = {
        'crops': crops,
    }
    return render(request, 'planting_schedule/crop_list.html', context)


def crop_create(request):
    """Create a new crop"""
    if request.method == 'POST':
        form = CropForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Crop created successfully!')
            return redirect('planting_schedule:crop_list')
    else:
        form = CropForm()

    context = {
        'form': form,
        'title': 'Create New Crop',
    }
    return render(request, 'planting_schedule/crop_form.html', context)


def crop_detail(request, pk):
    """View crop details"""
    crop = get_object_or_404(Crop, pk=pk)
    context = {
        'crop': crop,
    }
    return render(request, 'planting_schedule/crop_detail.html', context)


def crop_edit(request, pk):
    """Edit a crop"""
    crop = get_object_or_404(Crop, pk=pk)
    if request.method == 'POST':
        form = CropForm(request.POST, instance=crop)
        if form.is_valid():
            form.save()
            messages.success(request, 'Crop updated successfully!')
            return redirect('planting_schedule:crop_detail', pk=crop.pk)
    else:
        form = CropForm(instance=crop)

    context = {
        'form': form,
        'crop': crop,
        'title': 'Edit Crop',
    }
    return render(request, 'planting_schedule/crop_form.html', context)


def crop_delete(request, pk):
    """Delete a crop"""
    crop = get_object_or_404(Crop, pk=pk)
    if request.method == 'POST':
        crop.delete()
        messages.success(request, 'Crop deleted successfully!')
        return redirect('planting_schedule:crop_list')

    context = {
        'crop': crop,
    }
    return render(request, 'planting_schedule/crop_confirm_delete.html', context)


# Farm Block Views
def block_list(request):
    """List all farm blocks"""
    blocks = FarmBlock.objects.all().order_by('name')
    context = {
        'blocks': blocks,
    }
    return render(request, 'planting_schedule/block_list.html', context)


def block_create(request):
    """Create a new farm block"""
    if request.method == 'POST':
        form = FarmBlockForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Farm block created successfully!')
            return redirect('planting_schedule:block_list')
    else:
        form = FarmBlockForm()

    context = {
        'form': form,
        'title': 'Create New Farm Block',
    }
    return render(request, 'planting_schedule/block_form.html', context)


def block_detail(request, pk):
    """View farm block details"""
    farm_block = get_object_or_404(FarmBlock, pk=pk)
    context = {
        'farm_block': farm_block,
    }
    return render(request, 'planting_schedule/block_detail.html', context)


def block_edit(request, pk):
    """Edit a farm block"""
    farm_block = get_object_or_404(FarmBlock, pk=pk)
    if request.method == 'POST':
        form = FarmBlockForm(request.POST, instance=farm_block)
        if form.is_valid():
            form.save()
            messages.success(request, 'Farm block updated successfully!')
            return redirect('planting_schedule:block_detail', pk=farm_block.pk)
    else:
        form = FarmBlockForm(instance=farm_block)

    context = {
        'form': form,
        'farm_block': farm_block,
        'title': 'Edit Farm Block',
    }
    return render(request, 'planting_schedule/block_form.html', context)


def block_delete(request, pk):
    """Delete a farm block"""
    farm_block = get_object_or_404(FarmBlock, pk=pk)
    if request.method == 'POST':
        farm_block.delete()
        messages.success(request, 'Farm block deleted successfully!')
        return redirect('planting_schedule:block_list')

    context = {
        'farm_block': farm_block,
    }
    return render(request, 'planting_schedule/block_confirm_delete.html', context)
