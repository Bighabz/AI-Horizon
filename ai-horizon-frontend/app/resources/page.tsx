'use client';

import React, { useState, Suspense, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchResources } from '@/lib/api';
import { ResourceCard } from '@/components/cards/ResourceCard';
import { SearchBar } from '@/components/features/SearchBar';
import { Skeleton } from '@/components/ui/skeleton';
import { useSearchParams, useRouter } from 'next/navigation';
import {
    Pagination,
    PaginationContent,
    PaginationItem,
    PaginationLink,
    PaginationNext,
    PaginationPrevious
} from "@/components/ui/pagination";
import { Resource } from '@/lib/types';
import { CascadeFilter, FilterState } from '@/components/features/filter/CascadeFilter';

function ResourcesContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const page = parseInt(searchParams.get('page') || '1');

    // Read role filter from URL query param (from SkillCard navigation)
    const urlRole = searchParams.get('role') || 'All';

    const [searchQuery, setSearchQuery] = useState("");
    const [filters, setFilters] = useState<FilterState>({
        category: 'All',
        role: urlRole,
        taskId: 'All',
        classifications: []
    });

    // Sync URL role param with filters when URL changes
    useEffect(() => {
        if (urlRole !== filters.role) {
            setFilters(prev => ({ ...prev, role: urlRole }));
        }
    }, [urlRole]);

    // Get active filters for API call
    const roleFilter = filters.role !== 'All' ? filters.role : '';
    const taskFilter = filters.taskId !== 'All' ? filters.taskId : '';
    const classificationFilter = filters.classifications.length > 0 ? filters.classifications[0] : '';

    const handleFilterChange = useCallback((newFilters: FilterState) => {
        setFilters(newFilters);
    }, []);

    const { data, isLoading } = useQuery({
        queryKey: ['resources', page, searchQuery, roleFilter, taskFilter, classificationFilter],
        queryFn: () => fetchResources({
            page,
            limit: 20,
            query: searchQuery,
            job_role: roleFilter || undefined,
            dcwf_task: taskFilter || undefined,
            classification: classificationFilter || undefined,
        }),
        placeholderData: (prev) => prev,
    });

    const handlePageChange = (newPage: number) => {
        // Update URL params
        const params = new URLSearchParams(searchParams.toString());
        params.set('page', newPage.toString());
        router.push(`?${params.toString()}`);
    };

    const handleViewDetails = (id: string) => {
        router.push(`/evidence/${id}`);
    };

    // Check if any filters are active
    const hasActiveFilters = roleFilter || taskFilter || classificationFilter;

    // Build filter description
    const getFilterDescription = () => {
        const parts: string[] = [];
        if (roleFilter) parts.push(`Role: ${roleFilter}`);
        if (taskFilter) parts.push(`Task: ${taskFilter}`);
        if (classificationFilter) parts.push(`Classification: ${classificationFilter}`);
        return parts.length > 0 ? parts.join(' • ') : 'Browse analyzed artifacts including videos, courses, and articles.';
    };

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Evidence Library</h2>
                    <p className="text-muted-foreground">
                        {getFilterDescription()}
                    </p>
                </div>
                <SearchBar
                    value={searchQuery}
                    onChange={setSearchQuery}
                    className="w-full md:w-[300px]"
                />
            </div>

            {/* Filter Panel - key forces re-mount when URL role changes */}
            <CascadeFilter
                key={`filter-${urlRole}`}
                onFilterChange={handleFilterChange}
                initialFilters={{ role: urlRole }}
            />

            {isLoading ? (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {[...Array(8)].map((_, i) => (
                        <Skeleton key={i} className="h-[300px] rounded-xl" />
                    ))}
                </div>
            ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {data?.resources?.map((resource: Resource) => (
                        <ResourceCard
                            key={resource.artifact_id}
                            resource={resource}
                            onViewDetails={handleViewDetails}
                        />
                    ))}
                </div>
            )}

            {/* Pagination */}
            {data && data.total_pages > 1 && (
                <Pagination>
                    <PaginationContent>
                        <PaginationItem>
                            <PaginationPrevious
                                href="#"
                                onClick={(e) => { e.preventDefault(); if (page > 1) handlePageChange(page - 1); }}
                                className={page <= 1 ? "pointer-events-none opacity-50" : ""}
                            />
                        </PaginationItem>
                        {/* Simple Pagination Logic: Show current, prev, next */}
                        {page > 1 && (
                            <PaginationItem>
                                <PaginationLink href="#" onClick={(e) => { e.preventDefault(); handlePageChange(page - 1); }}>{page - 1}</PaginationLink>
                            </PaginationItem>
                        )}
                        <PaginationItem>
                            <PaginationLink href="#" isActive>{page}</PaginationLink>
                        </PaginationItem>
                        {page < data.total_pages && (
                            <PaginationItem>
                                <PaginationLink href="#" onClick={(e) => { e.preventDefault(); handlePageChange(page + 1); }}>{page + 1}</PaginationLink>
                            </PaginationItem>
                        )}
                        <PaginationItem>
                            <PaginationNext
                                href="#"
                                onClick={(e) => { e.preventDefault(); if (page < data.total_pages) handlePageChange(page + 1); }}
                                className={page >= data.total_pages ? "pointer-events-none opacity-50" : ""}
                            />
                        </PaginationItem>
                    </PaginationContent>
                </Pagination>
            )}
        </div>
    );
}

export default function ResourcesPage() {
    return (
        <Suspense fallback={<div className="p-8"><Skeleton className="h-[200px] w-full" /></div>}>
            <ResourcesContent />
        </Suspense>
    );
}
