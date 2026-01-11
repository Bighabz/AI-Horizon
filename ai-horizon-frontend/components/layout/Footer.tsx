import React from 'react';

export function Footer() {
    return (
        <footer className="border-t bg-muted/20 py-6 md:px-8 md:py-0">
            <div className="container flex flex-col items-center justify-between gap-4 md:h-24 md:flex-row">
                <p className="text-center text-sm leading-loose text-muted-foreground md:text-left">
                    Built for the <strong>AI Horizon Classification Pipeline</strong> research tool.
                    Data based on DCWF framework.
                </p>
                <p className="text-center text-sm text-muted-foreground md:text-right">
                    Academic Purpose Only
                </p>
            </div>
        </footer>
    );
}
