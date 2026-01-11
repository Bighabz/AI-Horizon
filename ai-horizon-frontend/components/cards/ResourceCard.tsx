import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ResourceTypeBadge } from "@/components/badges/ResourceTypeBadge";
import { DifficultyBadge } from "@/components/badges/StatusBadges";
import { ClassificationBadge } from "@/components/badges/ClassificationBadge";
import { Resource } from "@/lib/types";
import { ExternalLink, FileText, DollarSign, Unlock } from "lucide-react";

interface ResourceCardProps {
    resource: Resource;
    onViewDetails?: (id: string) => void;
}

export function ResourceCard({ resource, onViewDetails }: ResourceCardProps) {
    return (
        <Card className="flex flex-col h-full bg-card hover:border-primary/50 transition-colors">
            <CardHeader className="pb-3">
                <div className="flex justify-between items-start mb-2">
                    <ResourceTypeBadge type={resource.resource_type} />
                    <div className="flex gap-2">
                        <DifficultyBadge level={resource.difficulty} />
                        {resource.is_free ? (
                            <Badge variant="outline" className="border-green-500 text-green-500 flex items-center gap-1">
                                <Unlock className="w-3 h-3" /> Free
                            </Badge>
                        ) : (
                            <Badge variant="outline" className="border-yellow-500 text-yellow-500 flex items-center gap-1">
                                <DollarSign className="w-3 h-3" /> Premium
                            </Badge>
                        )}
                    </div>
                </div>
                <CardTitle className="text-base leading-snug line-clamp-2">
                    {resource.source_url ? (
                        <a href={resource.source_url} target="_blank" rel="noopener noreferrer" className="hover:underline flex items-center gap-1">
                            {resource.title} <ExternalLink className="w-3 h-3 inline" />
                        </a>
                    ) : (
                        <span>{resource.title}</span>
                    )}
                </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 pb-3">
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">Classification:</span>
                        <ClassificationBadge type={resource.classification} />
                    </div>

                    <div>
                        <span className="text-xs text-muted-foreground block mb-1">Impacted Roles:</span>
                        <div className="flex flex-wrap gap-1">
                            {resource.work_roles?.slice(0, 3).map((role, i) => (
                                <Badge key={i} variant="secondary" className="text-[10px] h-5">
                                    {role}
                                </Badge>
                            ))}
                            {(resource.work_roles?.length || 0) > 3 && (
                                <Badge variant="secondary" className="text-[10px] h-5">+{resource.work_roles.length - 3}</Badge>
                            )}
                        </div>
                    </div>

                    <p className="text-xs text-muted-foreground line-clamp-3 italic">
                        "{resource.rationale}"
                    </p>
                </div>
            </CardContent>
            <CardFooter className="pt-0">
                <Button variant="secondary" className="w-full" onClick={() => onViewDetails?.(resource.artifact_id)}>
                    <FileText className="w-4 h-4 mr-2" /> View Analysis
                </Button>
            </CardFooter>
        </Card>
    );
}
