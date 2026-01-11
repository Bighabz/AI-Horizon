import React from 'react';
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// Difficulty: Beginner (green), Intermediate (yellow), Advanced (orange), Expert (red)
const difficultyColors: Record<string, string> = {
    Beginner: "bg-green-500",
    Intermediate: "bg-yellow-500",
    Advanced: "bg-orange-500",
    Expert: "bg-red-500",
};

export const DifficultyBadge: React.FC<{ level: string; className?: string }> = ({ level, className }) => {
    const colorClass = Object.entries(difficultyColors).find(([k]) => k.toLowerCase() === level?.toLowerCase())?.[1] || "bg-slate-500";
    return (
        <Badge variant="outline" className={cn(`${colorClass} bg-opacity-10 text-${colorClass.replace('bg-', '')} border-${colorClass.replace('bg-', '')}`, className)}>
            {level}
        </Badge>
    );
};

// Priority: Critical (red), High (orange), Moderate (yellow)
const priorityColors: Record<string, string> = {
    Critical: "bg-red-600",
    High: "bg-orange-500",
    Moderate: "bg-yellow-500",
};

export const PriorityBadge: React.FC<{ priority: string; className?: string }> = ({ priority, className }) => {
    const colorClass = Object.entries(priorityColors).find(([k]) => k.toLowerCase() === priority?.toLowerCase())?.[1] || "bg-slate-500";
    return (
        <Badge className={cn(`${colorClass} hover:${colorClass}/80 text-white`, className)}>
            {priority} Priority
        </Badge>
    );
};
