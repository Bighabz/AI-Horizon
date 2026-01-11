'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchResourceDetail } from '@/lib/api';
import { ClassificationBadge } from '@/components/badges/ClassificationBadge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, ExternalLink, Calendar, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { EvidenceDetail } from '@/lib/types';

export default function EvidenceDetailPage() {
    const { id } = useParams();
    const { data: evidence, isLoading } = useQuery<EvidenceDetail>({
        queryKey: ['evidence', id],
        queryFn: () => fetchResourceDetail(id as string),
        enabled: !!id,
    });

    if (isLoading) return <div className="p-8">Loading evidence details...</div>;
    if (!evidence) return <div className="p-8">Evidence not found.</div>;

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            <Link href="/resources" className="inline-flex items-center text-sm text-muted-foreground hover:text-primary">
                <ArrowLeft className="mr-2 h-4 w-4" /> Back to Resources
            </Link>

            <div className="space-y-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <h1 className="text-3xl font-bold tracking-tight leading-tight">{evidence.title}</h1>
                    {evidence.source_url && (
                        <Button asChild>
                            <a href={evidence.source_url} target="_blank" rel="noopener noreferrer">
                                Visit Source <ExternalLink className="ml-2 h-4 w-4" />
                            </a>
                        </Button>
                    )}
                </div>

                <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                    <div className="flex items-center">
                        <Calendar className="mr-1 h-4 w-4" />
                        {new Date(evidence.stored_at).toLocaleDateString()}
                    </div>
                    <ClassificationBadge type={evidence.classification} className="text-sm px-3 py-1" />
                    <span className="text-xs bg-muted px-2 py-1 rounded">Confidence: {Math.round(evidence.confidence * 100)}%</span>
                </div>
            </div>

            <Separator />

            <div className="grid md:grid-cols-3 gap-8">
                {/* Main Content */}
                <div className="md:col-span-2 space-y-8">
                    <section>
                        <h3 className="text-xl font-semibold mb-3">Rationale</h3>
                        <Card>
                            <CardContent className="pt-6">
                                <p className="leading-relaxed text-muted-foreground">
                                    {evidence.rationale}
                                </p>
                            </CardContent>
                        </Card>
                    </section>

                    {evidence.key_findings && evidence.key_findings.length > 0 && (
                        <section>
                            <h3 className="text-xl font-semibold mb-3">Key Findings</h3>
                            <ul className="space-y-2">
                                {evidence.key_findings.map((finding: string, i: number) => (
                                    <li key={i} className="flex items-start gap-2">
                                        <CheckCircle2 className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                                        <span>{finding}</span>
                                    </li>
                                ))}
                            </ul>
                        </section>
                    )}
                </div>

                {/* Sidebar */}
                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base">Impacted Work Roles</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="flex flex-wrap gap-2">
                                {evidence.work_roles?.map((role: string) => (
                                    <Badge key={role} variant="secondary">{role}</Badge>
                                ))}
                            </div>
                        </CardContent>
                    </Card>

                    {evidence.dcwf_tasks && evidence.dcwf_tasks.length > 0 && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-base">Related DCWF Tasks</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                {evidence.dcwf_tasks.map((task: { task_id: string; task_name: string }) => (
                                    <div key={task.task_id} className="border-l-2 border-muted pl-3">
                                        <div className="font-semibold text-sm">{task.task_id}</div>
                                        <div className="text-xs text-muted-foreground line-clamp-2">{task.task_name}</div>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    )}
                </div>
            </div>
        </div>
    );
}
