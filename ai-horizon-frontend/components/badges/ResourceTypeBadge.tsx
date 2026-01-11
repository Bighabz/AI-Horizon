import React from 'react';
import { Badge } from "@/components/ui/badge";

interface ResourceTypeBadgeProps {
    type: string;
    className?: string;
}

// Colors from user brief
// Video (red), Course (blue), Certification (purple), Platform (teal), Article (orange), Tool (green), Bootcamp (pink)
const colorMap: Record<string, string> = {
    Video: "bg-red-500",
    Course: "bg-blue-500",
    Certification: "bg-purple-500",
    Platform: "bg-teal-500",
    Article: "bg-orange-500",
    Tool: "bg-green-500",
    Bootcamp: "bg-pink-500",
};

export const ResourceTypeBadge: React.FC<ResourceTypeBadgeProps> = ({ type, className }) => {
    // Simple check for known types, else default
    const colorClass = Object.entries(colorMap).find(([k]) => k.toLowerCase() === type?.toLowerCase())?.[1] || "bg-slate-500";

    return (
        <Badge className={`${colorClass} hover:${colorClass}/80 text-white border-transparent ${className}`}>
            {type}
        </Badge>
    );
};
