'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PriorityBadge } from "@/components/badges/StatusBadges";
import { ClassificationBadge } from "@/components/badges/ClassificationBadge";
import { SkillItem } from "@/lib/types";
import { Users, FileText, ArrowRight } from "lucide-react";
import { useRouter } from 'next/navigation';

interface SkillCardProps {
    skill: SkillItem;
}

// Determine dominant classification from counts
function getDominantClassification(classifications: SkillItem['classifications']): string {
    const entries = Object.entries(classifications) as [string, number][];
    const sorted = entries.sort((a, b) => b[1] - a[1]);
    return sorted[0]?.[0] || 'Augment';
}

// Calculate confidence based on classification distribution
function getConfidence(classifications: SkillItem['classifications']): number {
    const total = Object.values(classifications).reduce((a, b) => a + b, 0);
    if (total === 0) return 0.7;
    const max = Math.max(...Object.values(classifications));
    return max / total;
}

export function SkillCard({ skill }: SkillCardProps) {
    const router = useRouter();
    const dominantClassification = getDominantClassification(skill.classifications);
    const confidence = getConfidence(skill.classifications);

    const handleViewEvidence = () => {
        router.push(`/resources?role=${encodeURIComponent(skill.name)}`);
    };

    return (
        <Card
            className="h-full transition-all hover:border-primary/50 hover:shadow-lg bg-card cursor-pointer"
            onClick={handleViewEvidence}
        >
            <CardHeader className="space-y-1 pb-2">
                <div className="flex justify-between items-start">
                    <Badge variant="secondary" className="mb-2 line-clamp-1">{skill.id}</Badge>
                    <PriorityBadge priority={skill.priority.replace(' Priority', '') as 'Critical' | 'High' | 'Moderate' | 'Low'} />
                </div>
                <CardTitle className="leading-tight text-lg">{skill.name}</CardTitle>
                <CardDescription className="line-clamp-2 text-xs">
                    {skill.category}
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="flex flex-wrap gap-2 mt-2">
                    <div className="flex items-center text-xs text-muted-foreground">
                        <FileText className="mr-1 h-3 w-3" />
                        {skill.total_resources} Resources
                    </div>
                    <div className="flex items-center text-xs text-muted-foreground">
                        <Users className="mr-1 h-3 w-3" />
                        {skill.free_resources} Free
                    </div>
                </div>

                <div className="mt-4 space-y-2">
                    <div className="text-xs font-semibold text-muted-foreground">Dominant Classification</div>
                    <ClassificationBadge
                        type={dominantClassification as "Replace" | "Augment" | "Remain Human" | "New Task"}
                        className="w-full justify-center"
                    />
                    <div className="text-[10px] text-center text-muted-foreground mt-1">
                        {Math.round(confidence * 100)}% Confidence
                    </div>
                    <Button
                        variant="secondary"
                        className="w-full mt-2"
                        onClick={(e) => {
                            e.stopPropagation(); // Prevent card click from also firing
                            handleViewEvidence();
                        }}
                    >
                        View Evidence ({skill.total_resources})
                        <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}
