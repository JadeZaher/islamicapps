'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { LocationRecord } from '@/db/queries/contracts';
import { createLocation, deleteLocation, updateLocation } from '@/app/actions/curation/location';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Plus, Edit2 } from 'lucide-react';
import { ConfirmDelete } from '@/app/admin/_components/ConfirmDelete';
import { describeActionError, unwrapAction } from '@/app/admin/_components/actionError';
import { PaginationControls } from '@/components/PaginationControls';
import { SearchFilterBar } from '@/components/SearchFilterBar';

interface PaginationInfo {
    page: number;
    totalPages: number;
    total: number;
    pageSize: number;
}

interface LocationsManagerClientProps {
    locations: LocationRecord[];
    pagination: PaginationInfo;
    searchQuery?: string;
}

export function LocationsManagerClient({ locations, pagination, searchQuery = '' }: LocationsManagerClientProps) {
    const router = useRouter();
    const [isCreating, setIsCreating] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);
    const [formData, setFormData] = useState({
        name: '',
        modern_country: '',
        region: '',
        latitude: '',
        longitude: '',
    });

    const filteredLocations = searchQuery
        ? locations.filter((location) =>
              location.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
              (location.modern_country && location.modern_country.toLowerCase().includes(searchQuery.toLowerCase()))
          )
        : locations;

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        setFormError(null);
        try {
            await unwrapAction(createLocation(formData));
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
            setFormError(describeActionError(error, 'Could not create the location. Check the fields and try again.'));
        } finally {
            setIsSaving(false);
        }
    };

    const handleEdit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingId) return;
        setIsSaving(true);
        setFormError(null);
        try {
            await unwrapAction(updateLocation(editingId, formData));
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
            setFormError(describeActionError(error, 'Could not update the location. Check the fields and try again.'));
        } finally {
            setIsSaving(false);
        }
    };

    const handleDelete = async (locationId: string) => {
        await unwrapAction(deleteLocation(locationId));
        router.refresh();
    };

    const handleStartEdit = (location: LocationRecord) => {
        setEditingId(location.id);
        setFormData({
            name: location.name || '',
            modern_country: location.modern_country || '',
            region: location.region || '',
            latitude: location.latitude == null ? '' : String(location.latitude),
            longitude: location.longitude == null ? '' : String(location.longitude),
        });
        setIsCreating(false);
        setFormError(null);
    };

    return (
        <div>
            <div className="flex items-center justify-between mb-8">
                <h1 className="text-3xl font-bold text-ink">Locations</h1>
                <Button
                    onClick={() => {
                        setIsCreating(true);
                        setEditingId(null);
                        setFormError(null);
                        setFormData({
                            name: '',
                            modern_country: '',
                            region: '',
                            latitude: '',
                            longitude: '',
                        });
                    }}
                    className="bg-accent text-on-accent hover:bg-ink hover:text-paper"
                >
                    <Plus className="w-4 h-4 mr-2" />
                    New Location
                </Button>
            </div>

            <SearchFilterBar
                searchPlaceholder="Search by location name or country..."
                totalResults={pagination.total}
            />

            {/* Create/Edit Form */}
            {(isCreating || editingId) && (
                <Card className="pb-6 mb-6">
                    <h2 className="text-xl font-semibold text-ink mb-4">
                        {editingId ? 'Edit Location' : 'Create New Location'}
                    </h2>
                    <form onSubmit={editingId ? handleEdit : handleCreate} className="space-y-4" aria-busy={isSaving}>
                        {formError && (
                            <div role="alert" className="border border-danger bg-transparent p-3 text-sm text-danger">
                                {formError}
                            </div>
                        )}
                        <div>
                            <Label htmlFor="name" className="text-ink">
                                Location Name
                            </Label>
                            <Input
                                id="name"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                placeholder="e.g., Medina, Damascus, Baghdad"
                                required
                                className="mt-2 bg-surface border-control text-ink"
                            />
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="modern_country" className="text-ink">
                                    Modern Country
                                </Label>
                                <Input
                                    id="modern_country"
                                    value={formData.modern_country}
                                    onChange={(e) => setFormData({ ...formData, modern_country: e.target.value })}
                                    placeholder="e.g., Saudi Arabia"
                                    className="mt-2 bg-surface border-control text-ink"
                                />
                            </div>
                            <div>
                                <Label htmlFor="region" className="text-ink">
                                    Region
                                </Label>
                                <Input
                                    id="region"
                                    value={formData.region}
                                    onChange={(e) => setFormData({ ...formData, region: e.target.value })}
                                    placeholder="e.g., Hejaz"
                                    className="mt-2 bg-surface border-control text-ink"
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="latitude" className="text-ink">
                                    Latitude
                                </Label>
                                <Input
                                    id="latitude"
                                    type="number"
                                    step="0.00001"
                                    value={formData.latitude}
                                    onChange={(e) => setFormData({ ...formData, latitude: e.target.value })}
                                    placeholder="e.g., 24.46"
                                    className="mt-2 bg-surface border-control text-ink"
                                />
                            </div>
                            <div>
                                <Label htmlFor="longitude" className="text-ink">
                                    Longitude
                                </Label>
                                <Input
                                    id="longitude"
                                    type="number"
                                    step="0.00001"
                                    value={formData.longitude}
                                    onChange={(e) => setFormData({ ...formData, longitude: e.target.value })}
                                    placeholder="e.g., 39.61"
                                    className="mt-2 bg-surface border-control text-ink"
                                />
                            </div>
                        </div>

                        <div className="flex gap-3">
                            <Button type="submit" disabled={isSaving} className="bg-accent text-on-accent hover:bg-ink hover:text-paper">
                                {isSaving ? 'Saving...' : editingId ? 'Update' : 'Create'}
                            </Button>
                            <Button
                                type="button"
                                variant="outline"
                                disabled={isSaving}
                                onClick={() => {
                                    setIsCreating(false);
                                    setEditingId(null);
                                    setFormError(null);
                                }}
                                className="border-rule text-ink"
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
                    <Card key={location.id} className="pb-6">
                        <div className="flex items-start justify-between">
                            <div className="flex-1">
                                <h3 className="text-lg font-semibold text-ink mb-2">{location.name}</h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-ink">
                                    {location.modern_country && (
                                        <div>
                                            <span className="text-ink-muted">Country: </span>
                                            {location.modern_country}
                                        </div>
                                    )}
                                    {location.region && (
                                        <div>
                                            <span className="text-ink-muted">Region: </span>
                                            {location.region}
                                        </div>
                                    )}
                                    {location.latitude != null && location.longitude != null && (
                                        <div>
                                            <span className="text-ink-muted">Coordinates: </span>
                                            {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
                                        </div>
                                    )}
                                    <div>
                                        <span className="text-ink-muted">Review state: </span>
                                        {location.verification_status === 'unverified_seed' ? 'Seed, unverified' : location.verification_status.replaceAll('_', ' ')}
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-start gap-2">
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleStartEdit(location)}
                                    aria-label={`Edit ${location.name}`}
                                    className="border-rule text-ink"
                                >
                                    <Edit2 className="w-4 h-4" aria-hidden="true" />
                                </Button>
                                <ConfirmDelete
                                    itemName="location"
                                    consequence={`Retire "${location.name}"? It is hidden from every page. Nothing is erased and an audit record is kept. Refused while a live event refers to it.`}
                                    onConfirm={() => handleDelete(location.id)}
                                />
                            </div>
                        </div>
                    </Card>
                ))}

                {filteredLocations.length === 0 && (
                    <Card className="border-rule border-dashed py-8">
                        <p className="text-center text-ink-muted">
                            {locations.length === 0
                                ? 'No locations yet. Click "New Location" to create one.'
                                : 'No locations match your search.'}
                        </p>
                    </Card>
                )}

                <PaginationControls
                    page={pagination.page}
                    totalPages={pagination.totalPages}
                    total={pagination.total}
                    pageSize={pagination.pageSize}
                />
            </div>
        </div>
    );
}
