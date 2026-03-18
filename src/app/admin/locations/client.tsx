'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createLocation, deleteLocation, updateLocation } from '@/app/actions/graph-actions';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Plus, Trash2, Edit2 } from 'lucide-react';

interface LocationsManagerClientProps {
    locations: any[];
}

export function LocationsManagerClient({ locations }: LocationsManagerClientProps) {
    const router = useRouter();
    const [isCreating, setIsCreating] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [formData, setFormData] = useState({
        name: '',
        modern_country: '',
        region: '',
        latitude: '',
        longitude: '',
    });

    const filteredLocations = locations.filter((location) =>
        location.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (location.modern_country && location.modern_country.toLowerCase().includes(searchTerm.toLowerCase()))
    );

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const submitData = {
                ...formData,
                latitude: formData.latitude ? parseFloat(formData.latitude) : undefined,
                longitude: formData.longitude ? parseFloat(formData.longitude) : undefined,
            };
            await createLocation(submitData as any);
            setFormData({
                name: '',
                modern_country: '',
                region: '',
                latitude: '',
                longitude: '',
            });
            setIsCreating(false);
            router.refresh();
        } catch (error) {
            console.error('Error creating location:', error);
        }
    };

    const handleEdit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingId) return;
        try {
            const submitData = {
                ...formData,
                latitude: formData.latitude ? parseFloat(formData.latitude) : undefined,
                longitude: formData.longitude ? parseFloat(formData.longitude) : undefined,
            };
            await updateLocation(editingId, submitData as any);
            setFormData({
                name: '',
                modern_country: '',
                region: '',
                latitude: '',
                longitude: '',
            });
            setEditingId(null);
            router.refresh();
        } catch (error) {
            console.error('Error updating location:', error);
        }
    };

    const handleDelete = async (locationId: string) => {
        if (confirm('Are you sure you want to delete this location?')) {
            try {
                await deleteLocation(locationId);
                router.refresh();
            } catch (error) {
                console.error('Error deleting location:', error);
            }
        }
    };

    const handleStartEdit = (location: any) => {
        setEditingId(location.id);
        setFormData({
            name: location.name || '',
            modern_country: location.modern_country || '',
            region: location.region || '',
            latitude: location.latitude || '',
            longitude: location.longitude || '',
        });
        setIsCreating(false);
    };

    return (
        <div>
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white">Locations Manager</h1>
                    <p className="text-slate-400 mt-1">Manage historical Islamic locations</p>
                </div>
                <Button
                    onClick={() => {
                        setIsCreating(true);
                        setEditingId(null);
                        setFormData({
                            name: '',
                            modern_country: '',
                            region: '',
                            latitude: '',
                            longitude: '',
                        });
                    }}
                    className="bg-emerald-600 hover:bg-emerald-700"
                >
                    <Plus className="w-4 h-4 mr-2" />
                    New Location
                </Button>
            </div>

            {/* Search Bar */}
            <Card className="bg-slate-900 border-slate-700 p-6 mb-6">
                <Label htmlFor="search" className="text-slate-300 block mb-3">
                    Search Locations
                </Label>
                <Input
                    id="search"
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search by location name or country..."
                    className="bg-slate-800 border-slate-700 text-white"
                />
            </Card>

            {/* Create/Edit Form */}
            {(isCreating || editingId) && (
                <Card className="bg-slate-900 border-slate-700 p-6 mb-6">
                    <h2 className="text-xl font-semibold text-white mb-4">
                        {editingId ? 'Edit Location' : 'Create New Location'}
                    </h2>
                    <form onSubmit={editingId ? handleEdit : handleCreate} className="space-y-4">
                        <div>
                            <Label htmlFor="name" className="text-slate-300">
                                Location Name
                            </Label>
                            <Input
                                id="name"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                placeholder="e.g., Medina, Damascus, Baghdad"
                                required
                                className="mt-2 bg-slate-800 border-slate-700 text-white"
                            />
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="modern_country" className="text-slate-300">
                                    Modern Country
                                </Label>
                                <Input
                                    id="modern_country"
                                    value={formData.modern_country}
                                    onChange={(e) => setFormData({ ...formData, modern_country: e.target.value })}
                                    placeholder="e.g., Saudi Arabia"
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            </div>
                            <div>
                                <Label htmlFor="region" className="text-slate-300">
                                    Region
                                </Label>
                                <Input
                                    id="region"
                                    value={formData.region}
                                    onChange={(e) => setFormData({ ...formData, region: e.target.value })}
                                    placeholder="e.g., Hejaz"
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="latitude" className="text-slate-300">
                                    Latitude
                                </Label>
                                <Input
                                    id="latitude"
                                    type="number"
                                    step="0.00001"
                                    value={formData.latitude}
                                    onChange={(e) => setFormData({ ...formData, latitude: e.target.value })}
                                    placeholder="e.g., 24.46"
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            </div>
                            <div>
                                <Label htmlFor="longitude" className="text-slate-300">
                                    Longitude
                                </Label>
                                <Input
                                    id="longitude"
                                    type="number"
                                    step="0.00001"
                                    value={formData.longitude}
                                    onChange={(e) => setFormData({ ...formData, longitude: e.target.value })}
                                    placeholder="e.g., 39.61"
                                    className="mt-2 bg-slate-800 border-slate-700 text-white"
                                />
                            </div>
                        </div>

                        <div className="flex gap-3">
                            <Button type="submit" className="bg-emerald-600 hover:bg-emerald-700">
                                {editingId ? 'Update' : 'Create'}
                            </Button>
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => {
                                    setIsCreating(false);
                                    setEditingId(null);
                                }}
                                className="border-slate-600 text-slate-300"
                            >
                                Cancel
                            </Button>
                        </div>
                    </form>
                </Card>
            )}

            {/* Locations List */}
            <div className="space-y-3">
                {filteredLocations.map((location) => (
                    <Card key={location.id} className="bg-slate-900 border-slate-700 p-6">
                        <div className="flex items-start justify-between">
                            <div className="flex-1">
                                <h3 className="text-lg font-semibold text-white mb-2">{location.name}</h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-slate-300">
                                    {location.modern_country && (
                                        <div>
                                            <span className="text-slate-400">Country: </span>
                                            {location.modern_country}
                                        </div>
                                    )}
                                    {location.region && (
                                        <div>
                                            <span className="text-slate-400">Region: </span>
                                            {location.region}
                                        </div>
                                    )}
                                    {location.latitude && location.longitude && (
                                        <div>
                                            <span className="text-slate-400">Coordinates: </span>
                                            {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="flex gap-2">
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleStartEdit(location)}
                                    className="border-slate-600 text-slate-300"
                                >
                                    <Edit2 className="w-4 h-4" />
                                </Button>
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleDelete(location.id)}
                                    className="border-red-600/30 text-red-400 hover:bg-red-500/10"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </Button>
                            </div>
                        </div>
                    </Card>
                ))}

                {filteredLocations.length === 0 && (
                    <Card className="bg-slate-900/30 border-slate-800 border-dashed p-12">
                        <p className="text-center text-slate-400">
                            {locations.length === 0
                                ? 'No locations yet. Click "New Location" to create one.'
                                : 'No locations match your search.'}
                        </p>
                    </Card>
                )}
            </div>
        </div>
    );
}
