'use client';

import React, { useState, Suspense } from 'react';
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

function ResourcesContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const page = parseInt(searchParams.get('page') || '1');
    const roleFilter = searchParams.get('role') || '';
    const taskFilter = searchParams.get('task') || '';
    const [searchQuery, setSearchQuery] = useState("");

    const { data, isLoading } = useQuery({
        queryKey: ['resources', page, searchQuery, roleFilter, taskFilter],
        queryFn: () => fetchResources({
            page,
            limit: 20,
            query: searchQuery,
            job_role: roleFilter || undefined,
            dcwf_task: taskFilter || undefined,
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

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Evidence Library</h2>
                    <p className="text-muted-foreground">
                        {roleFilter
                            ? `Showing evidence for: ${roleFilter}`
                            : taskFilter
                            ? `Showing evidence for task: ${taskFilter}`
                            : 'Browse analyzed artifacts including videos, courses, and articles.'}
                    </p>
                    {(roleFilter || taskFilter) && (
                        <button
                            onClick={() => router.push('/resources')}
                            className="text-sm text-teal-400 hover:underline mt-1"
                        >
                            ← Clear filter
                        </button>
                    )}
                </div>
                <SearchBar
                    value={searchQuery}
                    onChange={setSearchQuery}
                    className="w-full md:w-[300px]"
                />
            </div>

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
